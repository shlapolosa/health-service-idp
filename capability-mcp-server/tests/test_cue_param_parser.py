"""Unit tests for the CUE parameter-block parser."""
from src.infrastructure.cue_param_parser import parse_parameter_block


def test_parses_vanilla_topology_policy():
    # Matches what `kubectl get policydefinition topology -o jsonpath='{.spec.schematic.cue.template}'`
    # returns empirically (starts directly with `parameter: {`, tab-indented).
    template = """parameter: {
\t// +usage=Specify the names of the clusters to select.
\tclusters?: [...string]
\t// +usage=Specify the label selector for clusters
\tclusterLabelSelector?: [string]: string
\t// +usage=Ignore empty cluster error
\tallowEmpty?: bool
\t// +usage=Specify the target namespace to deploy in the selected clusters.
\tnamespace?: string
}
"""
    rows = parse_parameter_block(template)
    names = [r["name"] for r in rows]
    assert "clusters" in names
    assert "clusterLabelSelector" in names
    assert "allowEmpty" in names
    assert "namespace" in names
    # Required = bare `:` (no `?`), all 4 here are optional
    assert all(r["required"] is False for r in rows)
    # +usage text captured as description
    desc = {r["name"]: r["description"] for r in rows}
    assert "clusters to select" in desc["clusters"]
    assert "label selector" in desc["clusterLabelSelector"]


def test_parses_required_and_default():
    template = """
parameter: {
  // +usage=Image to deploy
  image: string
  // +usage=Number of replicas
  replicas?: *1 | int
  // +usage=Image pull policy
  pullPolicy?: *"IfNotPresent" | "Always" | "Never"
}
"""
    rows = parse_parameter_block(template)
    by_name = {r["name"]: r for r in rows}
    assert by_name["image"]["required"] is True
    assert by_name["image"]["default"] == ""
    assert by_name["replicas"]["required"] is False
    assert by_name["replicas"]["default"] == "1"
    assert by_name["replicas"]["type"] == "int"
    assert by_name["pullPolicy"]["default"] == "IfNotPresent"


def test_returns_empty_on_no_parameter_block():
    template = "output: { foo: 1 }\n# nothing else here\n"
    rows = parse_parameter_block(template)
    assert rows == []


def test_skips_malformed_lines():
    template = """
parameter: {
  // +usage=ok
  name: string
  ### this is garbage
  // not a usage tag
  another?: int
}
"""
    rows = parse_parameter_block(template)
    names = [r["name"] for r in rows]
    assert "name" in names
    assert "another" in names


def test_pending_usage_resets_on_blank_line():
    """A blank line between +usage and the field should drop the description (so next field
    doesn't inherit a stale usage tag)."""
    template = """
parameter: {
  // +usage=stale

  fresh: string
}
"""
    rows = parse_parameter_block(template)
    assert rows[0]["description"] == ""
