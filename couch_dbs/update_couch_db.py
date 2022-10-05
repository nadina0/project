import json
import base64
import re
import subprocess
from copy import copy
from subprocess import PIPE, STDOUT
from argparse import ArgumentParser
import binascii

import requests

AVAILABLE_DBS = ["asr_hints", "expected_input", "nlg", "visual_output"]
DB_PORT = "5984"


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("database_partition", help="name of the database partition")
    parser.add_argument("project_namespace", help="namespace of the project")
    parser.add_argument(
        "--couchdb", default="couchdb-talkamatic", help="namespace of the CouchDB to update the data to"
    )
    return parser.parse_args()


class Database:
    KEY_FOR_INDEX = ""

    def __init__(self, project, partition, couchdb_namespace):
        self._project = project
        self._partition = partition
        self._session = requests.session()
        self._authenticate_in_couchdb(couchdb_namespace)
        self._potentially_create_db()
        self._db = self._session.get(
            f"http://127.0.0.1:{DB_PORT}/{project}/_partition/{partition}/_all_docs?include_docs=true"
        )
        self._db = json.loads(self._db.text).get("rows", [])
        self._new_docs = self._load_json_into_dict_indexed_on_match()

    def _authenticate_in_couchdb(self, couchdb_namespace):
        couchdb_user = "admin"
        command = [
            'kubectl', 'get', 'secret', f'{couchdb_namespace}-couchdb', '-o', 'jsonpath="{.data.adminPassword}"', '-n',
            f'{couchdb_namespace}'
        ]
        get_password = subprocess.Popen(command, stdout=PIPE, stderr=STDOUT)
        couchdb_password, stderr = get_password.communicate()
        couchdb_password = base64.b64decode(couchdb_password)
        self._session.auth = (couchdb_user, couchdb_password.decode("utf-8"))

    def _potentially_create_db(self):
        self._session.put(f"http://127.0.0.1:{DB_PORT}/{self._project}?partitioned=true")

    def _load_json_into_dict_indexed_on_match(self):
        filename = f"{self._partition}.json"
        with open(filename, "r") as json_file:
            docs = json.load(json_file)
        return {doc[self.KEY_FOR_INDEX]: doc for doc in docs}

    def _db_docs(self):
        for doc in self._db:
            yield doc["doc"]

    def process_doc_updates(self):
        keys_to_update, keys_to_delete = self._get_keys_to_update_and_delete_in_db()
        keys_to_add = self._get_keys_to_add_to_db()
        self._print_db_changes(keys_to_add, keys_to_delete, keys_to_update)

        docs_to_post = []
        docs_to_post.extend(self._get_docs_to_delete(keys_to_delete))
        docs_to_post.extend(self._get_docs_to_update(keys_to_update))
        docs_to_post.extend(self._get_docs_to_add(keys_to_add))
        self._post_new_docs_to_db(docs_to_post)

    def _get_keys_to_update_and_delete_in_db(self):
        def doc_in_db_exists_in_new_docs():
            return key_in_db in self._new_docs

        def delete_rev_and_id(doc):
            if "_id" in doc:
                del doc["_id"]
            if "_rev" in doc:
                del doc["_rev"]

        def doc_should_be_updated():
            doc_in_db_copy = copy(doc_in_db)
            doc_in_new_docs = self._new_docs[key_in_db]
            delete_rev_and_id(doc_in_db_copy)
            delete_rev_and_id(doc_in_new_docs)
            return doc_in_db_copy != doc_in_new_docs

        keys_to_update = []
        keys_to_delete = []
        for key_in_db, doc_in_db in self._existing_docs_in_db.items():
            if doc_in_db_exists_in_new_docs():
                if doc_should_be_updated():
                    keys_to_update.append(key_in_db)
            else:
                keys_to_delete.append(key_in_db)
        return keys_to_update, keys_to_delete

    def _get_keys_to_add_to_db(self):
        keys_to_add = []
        for new_doc_key in self._new_docs:
            if new_doc_key not in self._existing_docs_in_db:
                keys_to_add.append(new_doc_key)
        return keys_to_add

    def _print_db_changes(self, keys_to_add, keys_to_delete, keys_to_update):
        print(f"Docs to post in {self._partition} database")
        print("  Docs to add:", keys_to_add)
        print("  Docs to delete:", keys_to_delete)
        print("  Docs to update:", keys_to_update)

    def _get_docs_to_add(self, keys_to_add):
        new_docs = []
        for doc_id in keys_to_add:
            self._new_docs[doc_id]["_id"] = f"{self._partition}:{doc_id}"
            new_docs.append(self._new_docs[doc_id])
        return new_docs

    def _get_docs_to_update(self, keys_to_update):
        new_docs = []
        for doc_id in keys_to_update:
            self._new_docs[doc_id]["_id"] = f"{self._partition}:{doc_id}"
            self._new_docs[doc_id]["_rev"] = self._existing_docs_in_db[doc_id]["_rev"]
            new_docs.append(self._new_docs[doc_id])
        return new_docs

    def _get_docs_to_delete(self, keys_to_delete):
        new_docs = []
        for doc_key in keys_to_delete:
            doc_to_delete = self._existing_docs_in_db[doc_key]
            doc_to_delete["_id"] = f"{self._partition}:{doc_key}"
            doc_to_delete["_deleted"] = True
            new_docs.append(doc_to_delete)
        return new_docs

    def _post_new_docs_to_db(self, new_docs):
        new_docs = json.dumps({"docs": new_docs})
        self._session.post(
            f"http://127.0.0.1:{DB_PORT}/{self._project}/_bulk_docs",
            data=new_docs,
            headers={"Content-Type": "application/json"}
        )


class AsrHintsDatabase(Database):
    KEY_FOR_INDEX = "current_plan_item"

    def __init__(self, project, partition, couchdb_namespace):
        super().__init__(project, partition, couchdb_namespace)
        self._existing_docs_in_db = {doc[self.KEY_FOR_INDEX]: doc for doc in self._db_docs()}


class ExpectedInputDatabase(Database):
    def __init__(self, project, partition, couchdb_namespace):
        super().__init__(project, partition, couchdb_namespace)
        self._existing_docs_in_db = self._create_db_docs()

    def _create_key(self, expected_input_doc):
        current_plan_item = expected_input_doc["current_plan_item"]
        semantic_expression = expected_input_doc["semantic_expression"]
        return f"{current_plan_item}:{semantic_expression}"

    def _create_db_docs(self):
        db_docs = {}
        for doc in self._db_docs():
            key = self._create_key(doc)
            db_docs[key] = doc
        return db_docs

    def _load_json_into_dict_indexed_on_match(self):
        filename = f"{self._partition}.json"
        with open(filename, "r") as json_file:
            docs = json.load(json_file)

        new_docs = {}
        for doc in docs:
            key = self._create_key(doc)
            new_docs[key] = doc
        return new_docs


class NLGDatabase(Database):
    KEY_FOR_INDEX = "match"

    def __init__(self, project, partition, couchdb_namespace):
        super().__init__(project, partition, couchdb_namespace)
        self._existing_docs_in_db = {doc[self.KEY_FOR_INDEX]: doc for doc in self._db_docs()}


class VisualOutputDatabase(Database):
    KEY_FOR_INDEX = "semantic_expression"

    def __init__(self, project, partition, couchdb_namespace):
        super().__init__(project, partition, couchdb_namespace)
        self._existing_docs_in_db = {doc[self.KEY_FOR_INDEX]: doc for doc in self._db_docs()}


def dash(string):
    return re.sub("_", "-", string)


def main():
    args = parse_args()
    partition = args.database_partition
    project_namespace = f"db-{dash(args.project_namespace)}"
    couchdb_namespace = dash(args.couchdb)
    try:
        if partition == "asr_hints":
            db = AsrHintsDatabase(project_namespace, partition, couchdb_namespace)
        elif partition == "expected_input":
            db = ExpectedInputDatabase(project_namespace, partition, couchdb_namespace)
        elif partition == "nlg":
            db = NLGDatabase(project_namespace, partition, couchdb_namespace)
        elif partition == "visual_output":
            db = VisualOutputDatabase(project_namespace, partition, couchdb_namespace)
        db.process_doc_updates()
    except requests.exceptions.ConnectionError as e:
        print(
            f"ConnectionRefusedError: {e}"
            f"\n  Make sure that you have forwarded the CouchDB port ({DB_PORT}) of the namespace"
            f"\n  '{couchdb_namespace}' before running this script."
            f"\n  To forward the port {DB_PORT}, you can e.g. run the following command:"
            f"\n    kubectl port-forward svc/{couchdb_namespace}-svc-couchdb {DB_PORT} -n {couchdb_namespace} &"
        )
    except binascii.Error as e:
        print(
            f"binascii.Error: {e}"
            f"\n  Make sure the namespace {couchdb_namespace} exists in AWS."
        )  # yapf: disable
    except UnboundLocalError as e:
        print(
            f"UnboundLocalError: {e}"
            f"\n  Got {partition}, expected one of: {AVAILABLE_DBS}"
            f"\n  Make sure the database name is written correctly."
        )


if __name__ == "__main__":
    main()
