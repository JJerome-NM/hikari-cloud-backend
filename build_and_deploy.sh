#!/bin/bash

sam build

sam deploy --resolve-image-repos --parameter-overrides HikariCloudFrontend="https://jjerome-nm.github.io" HikariCloudFrontendCallbacks="https://jjerome-nm.github.io/hikari-cloud-frontend"

sam deploy --resolve-image-repos --parameter-overrides HikariCloudFrontend="http://localhost:5173" HikariCloudFrontendCallbacks="http://localhost:5173/hikari-cloud-frontend"
