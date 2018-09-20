# Cherry Tree

<img src="https://i.imgur.com/QGyxImm.jpg" title="Cherry Tree" width="250" />

Cherry Tree is a set of tools that were originally designed to help
build releases for
[Apache Superset](https://github.com/apache/incubator-superset),
but can be use for any other project
that wants to implement a similar workflow.

Ideas behind `cherrytree` include:
* Baking and storing release metadata in static, deterministic config files
* Github label driven development / releases
* Make release files from specifying base reference and Github labels
* Bake release branches/SHAs from said config files
* Follow a base reference + cherries approach

## An example build file

`cherrytree` offers tooling to both:
1. generate a "bake file" from a base git reference along with a set of tagged PRs
2. craft a branch in a target repo from a "bake file"

Here's an example "bake file":

```hocon
// this is a Hocon formatted file,
// learn more about hocon here https://github.com/lightbend/config/blob/master/HOCON.md
{
  id = "lyft.28.0rc4.1"
  base_ref = 0.28.0rc4
  source_repos = [
    'https://github.com/apache-superset/cherrytree',
    'https://github.com/some_fork/cherrytree',
  ]
  cherries = [
    [5e6efae15563036d98aa9a13affcef38c6957cb1, "Some SHA from either repos above"],
  ]
}
```

The format is `hocon`, which is yet another [bet much better] markup language.
