import json
import datetime
from pathlib import Path
from jinja2 import Template
import re
from datamodel_code_generator import InputFileType, generate
from pydantic import BaseModel

APP_TEMPLATE_STR = '''# generated by instructor-codegen:
#   timestamp: {{timestamp}}
#   task_name: {{task_name}}
#   api_path: {{api_path}}
#   json_schema_path: {{json_schema_path}}

from fastapi import FastAPI
from pydantic import BaseModel
from jinja2 import Template
from models import {{title}}

import openai
import instructor 

instructor.patch()

app = FastAPI()

class TemplateVariables(BaseModel):
{% for var in jinja_vars %}
    {{var.strip()}}: str
{% endfor %}

class RequestSchema(BaseModel):
    template_variables: TemplateVariables
    model: str
    temperature: int

PROMPT_TEMPLATE = Template("""{{prompt_template}}""".strip())

@app.post("{{api_path}}", response_model={{title}})
async def {{task_name}}(input: RequestSchema) -> {{title}}:
    rendered_prompt = PROMPT_TEMPLATE.render(**input.template_variables.model_dump())
    return await openai.ChatCompletion.acreate(
        model=input.model,
        temperature=input.temperature,
        response_model={{title}},
        messages=[
            {"role": "user", "content": rendered_prompt}
        ]
    ) # type: ignore
'''


class TemplateVariables(BaseModel):
    biography: str


def load_json_schema(json_schema_path: str) -> dict:
    try:
        with open(json_schema_path) as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load JSON schema: {e}")


def generate_pydantic_model(json_schema_path: str):
    input_path = Path(json_schema_path)
    output_path = Path("./models.py")
    generate(
        input_=input_path, input_file_type=InputFileType.JsonSchema, output=output_path
    )


def extract_jinja_vars(prompt_template: str) -> list:
    return re.findall(r"\{\{(.*?)\}\}", prompt_template)


def render_app_template(template_str: str, **kwargs) -> str:
    app_template = Template(template_str)
    return app_template.render(**kwargs)


def create_app(
    api_path: str, task_name: str, json_schema_path: str, prompt_template: str
) -> str:
    if not api_path.startswith("/"):
        api_path = "/" + api_path

    schema = load_json_schema(json_schema_path)
    title = schema["title"]
    generate_pydantic_model(json_schema_path)

    jinja_vars = extract_jinja_vars(prompt_template)

    return render_app_template(
        APP_TEMPLATE_STR,
        timestamp=datetime.datetime.now().isoformat(),
        task_name=task_name,
        api_path=api_path,
        json_schema_path=json_schema_path,
        title=title,
        jinja_vars=jinja_vars,
        prompt_template=prompt_template,
    )


if __name__ == "__main__":
    try:
        fastapi_code = create_app(
            api_path="/api/v1/extract_person",
            task_name="extract_person",
            json_schema_path="./input.json",
            prompt_template="Extract the person from the following: {{biography}}",
        )

        with open("./run.py", "w") as f:
            f.write(fastapi_code)

        print("FastAPI application generated and saved to './run.py'")

    except Exception as e:
        print(f"An error occurred: {e}")
