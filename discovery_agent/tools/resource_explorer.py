from typing import Annotated, Any, Dict, List, Optional
from strands.tools import tool
import boto3
import time

# Create a single session at module level - credentials loaded once
session = boto3.Session()

# Initialize AWS clients from the session
resource_explorer = session.client('resource-explorer-2')
aws_config_client = session.client('config')


@tool
def list_views() -> List[Dict[str, Any]]:
    """List Resource Explorer views.

    This tool retrieves all the AWS Resource Explorer views in the current AWS account and region,
    which can be used to find and filter resources for fault injection experiments.

    Returns:
        List of Resource Explorer views
    """
    try:
        all_views = []

        if resource_explorer is None:
            raise Exception(
                'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
            )
        response = resource_explorer.list_views()
        all_views.extend(response.get('Views', []))

        # Handle pagination
        while 'NextToken' in response:
            response = resource_explorer.list_views(NextToken=response['NextToken'])
            all_views.extend(response.get('Views', []))

        return all_views
    except Exception as e:
        return [{'error': f'Error listing Resource Explorer views: {str(e)}'}]


@tool
def search_resources(
    query_string: Annotated[str, 'The query string to search for resources'],
    view_arn: Annotated[str, 'The ARN of the Resource Explorer view to use'],
    max_results: Annotated[int, 'Maximum number of results to return'] = 100,
    next_token: Annotated[Optional[str], 'Token for pagination'] = None,
) -> Dict[str, Any]:
    """Search for AWS resources using Resource Explorer.

    This tool searches for AWS resources using Resource Explorer based on a query string
    and view ARN. It can be used to find specific resources for fault injection experiments.

    Args:
        query_string: The query string to search for resources
        view_arn: The ARN of the Resource Explorer view to use
        max_results: Maximum number of results to return (default: 100)
        next_token: Token for pagination (optional)

    Returns:
        Dict containing search results and pagination information
    """

    default_view =  resource_explorer.get_default_view()

    try:
        # Build search parameters
        search_params = {
            'QueryString': query_string,
            'ViewArn': default_view['ViewArn'],
            'MaxResults': max_results,
        }

        # Add next token if provided
        if next_token:
            search_params['NextToken'] = next_token

        if resource_explorer is None:
            raise Exception(
                'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
            )
        response = resource_explorer.search(**search_params)

        # Format results
        result = {
            'resources': response.get('Resources', []),
            'query_string': query_string,
            'view_arn': view_arn,
            'count': len(response.get('Resources', [])),
        }

        # Only include next_token if it exists in the response
        if 'NextToken' in response:
            result['next_token'] = response['NextToken']

        return result
    except Exception as e:
        return {'error': f'Error searching resources: {str(e)}'}


@tool
def create_view(
    query: Annotated[str, 'Filter string for the view'],
    view_name: Annotated[str, 'Name of the view'],
    name: Annotated[str, 'Required name for the view (will be added as Name tag)'],
    tags: Annotated[Optional[Dict[str, str]], 'Optional additional tags to apply to the view'] = None,
    scope: Annotated[Optional[str], 'Scope of the view'] = None,
    client_token: Annotated[Optional[str], 'Client token for idempotency'] = None,
) -> Dict[str, Any]:
    """Create a Resource Explorer view.

    This tool creates a new Resource Explorer view that can be used to find
    and filter resources for fault injection experiments.

    Args:
        query: Filter string for the view
        view_name: Name of the view
        name: Required name for the view (will be added as Name tag)
        tags: Optional additional tags to apply to the view
        scope: Scope of the view
        client_token: Client token for idempotency

    Returns:
        Dict containing the created view details
    """
    try:
        if resource_explorer is None:
            raise Exception(
                'AWS Resource Explorer client not initialized. Please ensure the server is properly configured.'
            )

        # Start with Name tag as required
        view_tags = {'Name': name}

        # Add any additional tags if provided
        if tags:
            view_tags.update(tags)

        # Generate client token if not provided
        if not client_token:
            client_token = f'create-view-{int(time.time())}'

        response = resource_explorer.create_view(
            ClientToken=client_token,
            Filters={'FilterString': query},
            Scope=scope,
            Tags=view_tags,
            ViewName=view_name,
        )

        return response
    except Exception as e:
        return {'error': f'Error creating Resource Explorer view: {str(e)}'}


@tool
def discover_relationships(
    resource_type: Annotated[str, 'AWS resource type (e.g., AWS::EC2::Instance, AWS::ElasticLoadBalancingV2::LoadBalancer)'],
    resource_id: Annotated[str, 'AWS resource ID to discover relationships for'],
    limit: Annotated[int, 'Maximum number of configuration items to retrieve'] = 10,
    chronological_order: Annotated[str, 'Order of configuration items (Reverse or Forward)'] = 'Reverse',
) -> Dict[str, Any]:
    """Discover relationships for a specific AWS resource using AWS Config.

    This tool retrieves the configuration history for a specific AWS resource
    and returns its relationships with other resources. This is useful for
    understanding resource dependencies, such as finding which subnet an ALB
    is placed in or which security groups are attached to an instance.

    Args:
        resource_type: AWS resource type (e.g., AWS::EC2::Instance)
        resource_id: AWS resource ID to discover relationships for
        limit: Maximum number of configuration items to retrieve
        chronological_order: Order of configuration items (Reverse or Forward)

    Returns:
        Dict containing resource relationships and configuration details
    """
    try:
        # Get resource configuration history
        params = {
            'resourceType': resource_type,
            'resourceId': resource_id,
            'chronologicalOrder': chronological_order,
            'limit': limit
        }

        if aws_config_client is None:
            raise Exception(
                'AWS Config client not initialized. Please ensure the server is properly configured.'
            )
        response = aws_config_client.get_resource_config_history(**params)

        result = {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'relationships': [],
            'configuration_items': [],
        }

        # Process configuration items
        config_items = response.get('configurationItems', [])

        if not config_items:
            result['message'] = 'No configuration items found for the specified resource'
            return result

        # Extract relationships from the most recent configuration item
        latest_config = config_items[0] if config_items else {}
        relationships = latest_config.get('relationships', [])

        result['relationships'] = relationships

        # Include configuration item details (without sensitive data)
        for item in config_items:
            config_summary = {
                'configuration_item_capture_time': str(
                    item.get('configurationItemCaptureTime', '')
                ),
                'configuration_state_id': item.get('configurationStateId'),
                'aws_region': item.get('awsRegion'),
                'availability_zone': item.get('availabilityZone'),
                'resource_creation_time': str(item.get('resourceCreationTime', '')),
                'tags': item.get('tags', {}),
                'relationships_count': len(item.get('relationships', [])),
            }
            result['configuration_items'].append(config_summary)

        # Add summary statistics
        result['summary'] = {
            'total_relationships': len(relationships),
            'total_configuration_items': len(config_items),
            'relationship_types': list({rel.get('relationshipName', '') for rel in relationships}),
        }

        return result

    except Exception as e:
        return {'error': f'Error discovering resource relationships: {str(e)}'}