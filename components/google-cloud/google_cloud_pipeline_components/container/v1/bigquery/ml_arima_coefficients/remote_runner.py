# Copyright 2022 The Kubeflow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging

import google.auth
import google.auth.transport.requests
from google_cloud_pipeline_components.container.v1.bigquery.utils import bigquery_util
from google_cloud_pipeline_components.container.v1.gcp_launcher.utils import artifact_util


def bigquery_ml_arima_coefficients(
    type,
    project,
    location,
    model_name,
    payload,
    job_configuration_query_override,
    gcp_resources,
    executor_input,
):
  """Create and poll bigquery ML.ARIMA_COEFFICIENTS job till it reaches a final state.

  The launching logic is the same as bigquery_{predict|evaluate}_model_job.

  Args:
      type: BigQuery ML.ARIMA_COEFFICIENTS job type.
      project: Project to launch the query job.
      location: location to launch the query job. For more details, see
        https://cloud.google.com/bigquery/docs/locations#specifying_your_location
      model_name: BigQuery ML model name for ML.ARIMA_COEFFICIENTS. For more
        details, see
      https://cloud.google.com/bigquery-ml/docs/reference/standard-sql/bigqueryml-syntax-arima-coefficients
      payload: A json serialized Job proto. For more details, see
        https://cloud.google.com/bigquery/docs/reference/rest/v2/Job
      job_configuration_query_override: A json serialized JobConfigurationQuery
        proto. For more details, see
        https://cloud.google.com/bigquery/docs/reference/rest/v2/Job#JobConfigurationQuery
      gcp_resources: File path for storing `gcp_resources` output parameter.
      executor_input:A json serialized pipeline executor input.
  """
  job_configuration_query_override_json = json.loads(
      job_configuration_query_override, strict=False
  )
  job_configuration_query_override_json['query'] = (
      'SELECT * FROM ML.ARIMA_COEFFICIENTS(MODEL %s)'
      % (bigquery_util.back_quoted_if_needed(model_name))
  )

  creds, _ = google.auth.default()
  job_uri = bigquery_util.check_if_job_exists(gcp_resources)
  if job_uri is None:
    job_uri = bigquery_util.create_query_job(
        project,
        location,
        payload,
        json.dumps(job_configuration_query_override_json),
        creds,
        gcp_resources,
    )

  # Poll bigquery job status until finished.
  job = bigquery_util.poll_job(job_uri, creds)
  logging.info('Getting query result for job ' + job['id'])
  _, job_id = job['id'].split('.')
  query_results = bigquery_util.get_query_results(
      project, job_id, location, creds
  )
  artifact_util.update_output_artifact(
      executor_input,
      'arima_coefficients',
      '',
      {
          bigquery_util.ARTIFACT_PROPERTY_KEY_SCHEMA: query_results[
              bigquery_util.ARTIFACT_PROPERTY_KEY_SCHEMA
          ],
          bigquery_util.ARTIFACT_PROPERTY_KEY_ROWS: query_results[
              bigquery_util.ARTIFACT_PROPERTY_KEY_ROWS
          ],
      },
  )
