# Examples

No patient-level DICOM, NIfTI, MRML, STL, or identifiable screenshots are
included.

The automated tests create synthetic arrays in memory. Run:

```bash
python -m unittest discover -s tests -v
```

For public demonstrations, use:

- synthetic CT-like volumes;
- programmatically generated femoral-head phantoms;
- de-identified masks approved for public release;
- screenshots with all metadata removed.

Do not treat a synthetic test as evidence of clinical segmentation accuracy.
