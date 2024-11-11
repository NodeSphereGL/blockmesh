#!/bin/bash

echo "Running prover with EMAIL: $EMAIL"

# Run the prover binary with the endpoint URL
/usr/local/bin/blockmesh-cli --email "$EMAIL" --password "$PASSWORD"
