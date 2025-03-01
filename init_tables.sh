#!/bin/bash

aws dynamodb create-table --cli-input-json file://db-json/create-photos-table.json --endpoint-url http://localhost:8000

aws dynamodb create-table --cli-input-json file://db-json/create-folders-table.json --endpoint-url http://localhost:8000

aws dynamodb create-table --cli-input-json file://db-json/create-sharing-table.json --endpoint-url http://localhost:8000
