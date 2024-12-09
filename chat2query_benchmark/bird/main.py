import glob
import json
import logging
import os

from svc import create_data_summary, loopv2, query_ai_for_sql

base_url = os.getenv("BASE_URL")
public_key = os.getenv("PUBLIC_KEY")
private_key = os.getenv("PRIVATE_KEY")


logging.basicConfig(level=logging.INFO)


def parse_cases(data_summary_id, bird_json_filename, dbname):
    with open(bird_json_filename) as f:
        result = json.loads(f.read())
        for i in result:
            database = i["db_id"]
            question = i["question"]
            evidence = i["evidence"]
            question_id = i["question_id"]

            if database not in [dbname, dbname.removeprefix("new_")]:
                continue

            try:
                generated_sql, description, clarified_task, raw_generated_sql, refine_note = query_ai_for_sql(data_summary_id, question, evidence)  # noqa
                if not generated_sql:
                    logging.warning(
                        "no sql found, data_summary_id %s, std spider args %s, results %s, %s, %s, %s, %s",
                        data_summary_id, i, generated_sql, description, clarified_task, raw_generated_sql, refine_note,  # noqa
                    )
                    generated_sql = "sql not found"

                generated_sql = generated_sql.replace("\n", " ").replace("\t", " ").replace("\r", " ").replace(";", "")

                yield (question_id, generated_sql, database)
            except Exception as e:
                logging.exception("failed to query_ai_for_sql: %s, retry after 5 seconds", e)
                yield (question_id, "sql not generated", database)


def run_db_cases():
    cases_filename = "./data/dev.json"
    output_filename = "./exp_result/turbo_output/predict_dev.json"

    results = {}
    for dbname in get_all_db_names():
        data_context_id, job_id = create_data_summary(dbname)
        loopv2(job_id)

        for (question_id, generated_sql, database) in parse_cases(data_context_id, cases_filename, dbname):
            results[str(question_id)] = generated_sql + "\t----- bird -----\t" + database

    with open(output_filename, 'w', newline='') as output_file:
        output_file.write(json.dumps(results, indent=4))


def parse_bird_cases():
    with open("./data/dev.json") as f:
        data = json.load(f)
        return data


def gen_sqlite_url(db_name: str):
    # bird/dev_databases/formula_1/formula_1.sqlite
    return "bird://{}".format(db_name)


def get_all_db_names():
    for i in glob.glob("./data/dev_databases/**/*.sqlite"):

        yield i.split("/")[-2]


if __name__ == "__main__":
    if not (base_url and public_key and private_key):
        print("Missing environment variables: BASE_URL, PUBLIC_KEY, PRIVATE_KEY")
        exit(1)

    run_db_cases()
