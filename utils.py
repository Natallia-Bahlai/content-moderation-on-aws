import botocore
import botocore.exceptions

def create_bda_project(project_name: str, project_description: str):

    try:
        response = bda.create_data_automation_project(
            projectName=project_name,
            projectDescription=project_description,
            standardOutputConfiguration={
                "audio": {
                    "extraction": {
                        "category": {"state": "ENABLED", "types": ["TRANSCRIPT"]}
                    },
                    "generativeField": {"state": "DISABLED", "types": []},
                },
                "video": {
                    "extraction": {
                        "category": {"state": "ENABLED", "types": ["CONTENT_MODERATION"]},
                        "boundingBox": {"state": "DISABLED"},
                    },
                    "generativeField": {
                        "state": "ENABLED",
                        "types": ["VIDEO_SUMMARY", "SCENE_SUMMARY"],
                    },
                },
                "image": {
                    "extraction": {
                        "category": {"state": "ENABLED", "types": ["CONTENT_MODERATION"]},
                        "boundingBox": {"state": "DISABLED"},
                    },
                    "generativeField": {"state": "ENABLED", "types": ["IMAGE_SUMMARY"]},
                },
                "document": {
                    "extraction": {
                        "granularity": {"types": ["PAGE", "ELEMENT"]},
                        "boundingBox": {"state": "DISABLED"},
                    },
                    "generativeField": {"state": "DISABLED"},
                    "outputFormat": {
                        "textFormat": {"types": ["MARKDOWN", "HTML"]},
                        "additionalFileFormat": {"state": "DISABLED"},
                    },
                },
            },
            customOutputConfiguration={"blueprints": []},
        )
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            print("Using existing Data Automation project")
            return get_bda_project_arn(project_name)
        else:
            raise e

    project_arn = response["projectArn"]
    creation_status = response["status"]

    max_wait_time = 60
    while creation_status == "IN_PROGRESS":
        creation_status = bda.get_data_automation_project(
            projectArn=project_arn
        )["project"]["status"]

        print(f"Project creation status: {creation_status}")
        time.sleep(5)
        max_wait_time -= 5

        if max_wait_time <= 0:
            raise TimeoutError("Project creation took too long")

    if creation_status == "COMPLETED":
        return project_arn
    else:
        raise Exception(f"Project creation failed with status: {creation_status}")
def get_json_object_from_s3_uri(s3_uri) -> dict:
    s3_uri_split = s3_uri.split('/')
    bucket = s3_uri_split[2]
    key = '/'.join(s3_uri_split[3:])
    object_content = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
    return json.loads(object_content)

def print_results(job_metadata_s3_uri) -> None:
    job_metadata = get_json_object_from_s3_uri(job_metadata_s3_uri)
    log(job_metadata)

    for segment in job_metadata['output_metadata']:
        asset_id = segment['asset_id']
        print(f'\nAsset ID: {asset_id}')

        for segment_metadata in segment['segment_metadata']:
            # Standard output
            standard_output_path = segment_metadata['standard_output_path']
            standard_output_result = get_json_object_from_s3_uri(standard_output_path)
            log(standard_output_result)
            print('\n- Standard output')
            semantic_modality = standard_output_result['metadata']['semantic_modality']
            print(f"Semantic modality: {semantic_modality}")
            match semantic_modality:
                case 'DOCUMENT':
                    print_document_results(standard_output_result)
                case 'VIDEO':
                    print_video_results(standard_output_result)
            # Custom output
            if 'custom_output_status' in segment_metadata and segment_metadata['custom_output_status'] == 'MATCH':
                custom_output_path = segment_metadata['custom_output_path']
                custom_output_result = get_json_object_from_s3_uri(custom_output_path)
                print_custom_results(custom_output_result)
                