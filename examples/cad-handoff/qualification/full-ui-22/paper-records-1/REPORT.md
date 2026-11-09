# Native paper records do not preserve the original sheets

Post-observation diagnosis on exposed cases; raw IDs/owners cross-check decoded inventories; no model or native invocation.

| Case / route | Layout | Paper / rotation changes | Display viewport |
|---|---|---|---|
| validation-cp1251 / noedit_native | Layout1 | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | No source display viewport to preserve |
| validation-cp1251 / noedit_native | Qualification sheet | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | Original display viewport missing |
| validation-cp1251 / concurrent_native | Layout1 | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | No source display viewport to preserve |
| validation-cp1251 / concurrent_native | Qualification sheet | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | Original display viewport missing |
| validation-braces / noedit_native | Layout1 | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | No source display viewport to preserve |
| validation-braces / noedit_native | Qualification sheet | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | Original display viewport missing |
| validation-braces / concurrent_native | Layout1 | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | No source display viewport to preserve |
| validation-braces / concurrent_native | Qualification sheet | paper_size: A3 → ISO_A4_(210.00_x_297.00_MM); paper_width: 420.0 → 210.0; plot_rotation: 0 → 1 | Original display viewport missing |

The complete [record audit](RESULT.json) retains all layouts, raw LAYOUT/VIEWPORT tags, owners and exact source hashes. Layout1 originally has no display viewport; it is not counted as a removed display viewport. Qualification sheet originally has ID3; native returns contain only a generated ID1.

The no-edit and concurrent native paths both change paper settings and omit the original display viewport. Attribute candidates retain their own source paper records, including pre-existing losses. Native round-trip paper preservation fails; exact import/save cause and rendered paper acceptance are not established.

This does not explain or waive every strict difference. It does not locate the precise installed importer/writer function. Source originals and all comparator rules remain unchanged.
