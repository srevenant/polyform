# Polyform

<i>Proof of Concept</i>

Polyforms are functions-as-a-service which include DataOps, specifically oriented
for running AI systems:

- are designed for native AI functionality
- have an explicit expectation of the shape of data sent to them
- support different sub-forms for variant purposes (such as training, vs intersect)
- support transformation of data in flight, as well as storing back to the data universe
- come with the implicit security of the Data Multiverse

Data Expectations describe the shape of the data as needed, and draw it in on
demand.

This code is a combination of a very rough implementation (prototype)
to prove the concept, combined with CI/CD automation for ease of use.

It is targeted towards the data science industry, enabling deep learning to be
more easily managed as production ready services.

```bash
pip3 install 'git+ssh://git@github.com/srevenant/polyform.git@master#egg=polyform'
```

Run `poly` with no args for a breakdown of options

Tutorial coming soon
