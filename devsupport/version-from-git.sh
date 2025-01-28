#!/bin/bash

VERSION=$(uvx dunamai from any)
uvx --from=toml-cli toml set --toml-path=pyproject.toml project.version $VERSION

echo "Set version to $VERSION"

exit 0
