import yaml
import os
from collections import defaultdict, Counter


d = yaml.load(open("/Users/alexbuchanan/dev/platform/oss/airbyte-api/server-api/src/main/openapi/config.yaml"), Loader=yaml.Loader)
print(d.keys())

class Group:
    def __init__(self):
        self.refs = []
        self.paths = []

    def unique_ref_names(self):
        return sorted(list(set(r[0] for r in self.refs)))

groups = defaultdict(Group)

def walk(defn, path, refs):
    if isinstance(defn, dict):
        for k, v in defn.items():
            if k == "$ref":
                refs.append([v, path])
            else:
                walk(v, path + [k], refs)
    if isinstance(defn, list):
        for i, v in enumerate(defn):
            walk(v, path + [str(i)], refs)


for path, defn in d["paths"].items():
    # print(path)
    sp = path.split("/")[1:]

    group_name = ""
    if sp[0] == "public":
        group_name = "public"
    else:
        group_name = sp[1]

    if group_name == "attempt":
        group_name = "jobs"
    if group_name == "source_oauths":
        group_name = "oauths"
    if group_name == "destination_oauths":
        group_name = "oauths"
    if "definition" in group_name:
        group_name = "definitions"

    group = groups[group_name]
    group.paths.append(path)
    walk(defn, ["paths", path], group.refs)
    
refcount = defaultdict(set)

for group_name, group in groups.items():
    print()
    print(group_name)
    print("-"*20)
    for p in sorted(group.paths):
        print(p)

    for r in group.unique_ref_names():
        # print(r)
        refcount[r].add(group_name)
        # refcount[r] += 1

print()
for refname, g in refcount.items():
    if len(g) > 1:
        print(refname, g)

def walk_replace(defn):
    if isinstance(defn, dict):
        if "$ref" in defn:
            ref = defn["$ref"]
            if len(refcount[ref]) > 1:
                defn["$ref"] = common.yaml + ref
        
        for k, v in defn.items():
            walk_replace(v, path + [k], refs)

    if isinstance(defn, list):
        for i, v in enumerate(defn):
            walk_replace(v, path + [str(i)], refs)

def write_group_specs(groups, output_dir):
    for group_name, group in groups.items():
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{group_name.capitalize().replace('_', ' ')} API",
                "version": "1.0.0"
            },
            "paths": {},
            "components": {
                "schemas": {},
                "responses": {},
            }
        }

        for path in group.paths:
            openapi_spec["paths"][path] = d["paths"][path]

        for ref in group.unique_ref_names():
            if len(refcount[ref]) > 1:
                # print("Skipping", ref)
                continue
            
            sp = ref.split("/")
            schema_name = sp[-1]
            ns = sp[2]
            openapi_spec["components"][ns][schema_name] = d["components"][ns][schema_name]

        # Write the OpenAPI spec to a YAML file
        output_path = os.path.join(output_dir, f"{group_name}.yaml")
        with open(output_path, "w") as f:
            yaml.dump(openapi_spec, f, sort_keys=False)

# Define the output directory
output_dir = "/Users/alexbuchanan/dev/split-api-specs/output"
os.makedirs(output_dir, exist_ok=True)

# Call the function to write the group specs
write_group_specs(groups, output_dir)


common_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": f"common API",
        "version": "1.0.0"
    },
    "paths": {},
    "components": {
        "schemas": {},
        "responses": {},
    }
}

for ref, g in refcount.items():
    if len(g) > 1:
        print(ref, g)

    sp = ref.split("/")
    schema_name = sp[-1]
    ns = sp[2]
    common_spec["components"][ns][schema_name] = d["components"][ns][schema_name]

# Write the OpenAPI spec to a YAML file
output_path = os.path.join(output_dir, f"common.yaml")
with open(output_path, "w") as f:
    yaml.dump(common_spec, f, sort_keys=False)