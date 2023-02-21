import json
import os
from typing import Dict
import pandas as pd
import requests


def read_csv(outdir: str, chat_id, df_columns) -> pd.DataFrame:
    try:
        df = pd.read_csv(os.path.join(outdir, f"{chat_id}.csv"))
    except Exception:
        df = pd.DataFrame(columns=df_columns)

    return df


def write_csv(df, outdir: str, chat_id):
    df.to_csv(os.path.join(outdir, f"{chat_id}.csv"), header=True, index=False)


def read_config(outdir: str) -> Dict:
    with open(f"{outdir}/env.json") as file:
        config = json.load(file)
    return config


def run_request(
    request_type: str,
    url: str,
    request_body: Dict[str, str] = {},
    request_json: str = "",
    bearer="",
    timeout: int = 30,
    media: Dict = None,
    request_headers=None,
    num_of_tries=1,
) -> Dict:
    success = False
    response = None
    expected_status_code = None
    try_number = 1

    while not success and try_number <= num_of_tries:
        try_number = try_number + 1
        try:
            if request_type == "GET":
                expected_status_code = 200
                if request_headers is None:
                    request_headers = {"Content-Type": "application/json", "Authorization": bearer}
                response = requests.get(url=url, headers=request_headers, params=request_body, timeout=timeout)
            elif request_type == "POST":
                expected_status_code = 200
                if media is not None:
                    response = requests.post(url, request_body, files=media, timeout=timeout)
                else:
                    response = requests.post(
                        url=url, headers={"Content-Type": "application/json"}, json=request_body, timeout=timeout
                    )
            elif request_type == "PATCH":
                expected_status_code = 200
                response = requests.patch(
                    url=url, headers={"Content-Type": "application/json"}, data=request_json, timeout=timeout
                )
            else:
                raise Exception("Wrong request type!")
            success = True
        except Exception as e:
            print(e)

    if not success:
        raise Exception(f"The request failed {num_of_tries} times.")

    if response.status_code != expected_status_code:
        raise Exception(response.content.decode("UTF-8"))

    return json.loads(response.content.decode("UTF-8"))
