import os
from ibm_watsonx_ai.foundation_models import ModelInference
from dotenv import load_dotenv
from ibmcloudant.cloudant_v1 import CloudantV1
from ibm_watsonx_ai import APIClient, Credentials

load_dotenv()



# ---------------------------------------------------------
# IBM watsonx.ai
# ---------------------------------------------------------

watsonx_credentials = Credentials(
    url=os.environ["WATSONX_URL"],
    api_key=os.environ["WATSONX_API_KEY"],
)

watsonx_client = APIClient(
    credentials=watsonx_credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)


# ---------------------------------------------------------
# Smoke test
# ---------------------------------------------------------

model = ModelInference(
    model_id="ibm/granite-4-h-small",
    api_client=watsonx_client,
)

response = model.chat(
    messages=[
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user",   "content": "Say hello in exactly one sentence."},
    ],
    params={"max_tokens": 200},
)

print(response["choices"][0]["message"]["content"])