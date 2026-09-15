# Experimental 1D-CNN add-on

This folder contains the engineering-form implementation of the separate 1D-CNN experiment that was originally developed alongside the EE6019 notebook workflow.

It consumes the same engineered temporal feature representation as the classical-ML pipeline. It is retained as an experimental comparison only; it is **not** the canonical headline benchmark reported for the project.

## Use

Install the main package first, then install the optional dependency:

```bash
pip install -e .
pip install -r extensions/cnn/requirements.txt
```

The implementation is in `cnn_addon.py`. The historical notebook is retained only as a cleaned reference under `notebooks/reference/`.
