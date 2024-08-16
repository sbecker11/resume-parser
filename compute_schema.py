import json
import sys
from genson import SchemaBuilder

def main():
    if len(sys.argv) != 3:
        print("Usage: python compute_schema.py <data>.json <data>-schema.json")
        sys.exit(1)

    data_file = sys.argv[1]
    schema_file = sys.argv[2]

    # Read the JSON data from the input file
    with open(data_file, 'r') as f:
        data = json.load(f)

    # Compute the JSON schema
    builder = SchemaBuilder()
    builder.add_object(data)
    schema = builder.to_schema()

    # Write the computed schema to the output file
    with open(schema_file, 'w') as f:
        json.dump(schema, f, indent=4)

if __name__ == "__main__":
    main()