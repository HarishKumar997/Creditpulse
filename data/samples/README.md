# Sample fixtures

These three customers show the CSV contract. They are synthetic and are not loaded by the pipeline.

The pipeline writes a seeded batch under `data/generated/`, which is gitignored. Tests build their own temporary batches with the generator so the expected reject and duplicate counts stay fixed.
