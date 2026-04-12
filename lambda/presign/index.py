"""
Walk-Up Songs — Presigned URL generator
Runtime: Python 3.12 (boto3 included in managed runtime)

Endpoints (called via CloudFront /api/*):
  GET /api/presign/list               — list all backup zips in the audio bucket
  GET /api/presign/upload?filename=x  — presigned PUT URL (5 min) for direct browser upload
  GET /api/presign/download?filename=x— presigned GET URL (30 min) for direct browser download

Security:
  Every request must carry the X-CloudFront-Secret header with the value
  stored in the CLOUDFRONT_SECRET environment variable. CloudFront injects
  this header automatically via Origin Custom Headers. Requests that arrive
  without the correct secret (i.e. anything that bypasses CloudFront) are
  rejected with 403.

Environment variables (set by CloudFormation):
  AUDIO_BUCKET      — name of the S3 bucket that stores zip exports
  CLOUDFRONT_SECRET — shared secret between CloudFront and this Lambda
"""

import json
import boto3
import os

s3 = boto3.client('s3')
BUCKET = os.environ['AUDIO_BUCKET']
SECRET = os.environ['CLOUDFRONT_SECRET']


def resp(code, body):
    return {
        'statusCode': code,
        'headers': {
            'Content-Type': 'application/json',
            # Same-origin when called via CloudFront, but included for
            # direct testing convenience.
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(body),
    }


def handler(event, context):
    # ── Auth ──────────────────────────────────────────────────────────────
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    if headers.get('x-cloudfront-secret') != SECRET:
        return {'statusCode': 403, 'body': 'Forbidden'}

    path = event.get('rawPath', '/')
    qs   = event.get('queryStringParameters') or {}

    # ── GET /api/presign/list ─────────────────────────────────────────────
    if path.endswith('/list'):
        result = s3.list_objects_v2(Bucket=BUCKET)
        files = [
            {
                'key':          o['Key'],
                'size':         o['Size'],
                'lastModified': o['LastModified'].isoformat(),
            }
            for o in result.get('Contents', [])
        ]
        # Most-recent first
        files.sort(key=lambda f: f['lastModified'], reverse=True)
        return resp(200, files)

    # ── GET /api/presign/upload?filename=<name.zip> ───────────────────────
    if path.endswith('/upload'):
        filename = qs.get('filename', '').strip()
        if not filename:
            return resp(400, {'error': 'filename query parameter is required'})
        # Enforce .zip extension to limit what can be stored
        if not filename.endswith('.zip'):
            filename = filename + '.zip'
        url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket':      BUCKET,
                'Key':         filename,
                'ContentType': 'application/zip',
            },
            ExpiresIn=300,   # 5 minutes — enough for any realistic upload
        )
        return resp(200, {'url': url, 'filename': filename})

    # ── GET /api/presign/download?filename=<name.zip> ─────────────────────
    if path.endswith('/download'):
        filename = qs.get('filename', '').strip()
        if not filename:
            return resp(400, {'error': 'filename query parameter is required'})
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': filename},
            ExpiresIn=1800,  # 30 minutes
        )
        return resp(200, {'url': url})

    return {'statusCode': 404, 'body': 'Not found'}
