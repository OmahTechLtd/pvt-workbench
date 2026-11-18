# PVT Workbench

A web tool for comparing published correlations for crude oil properties.

PVT Workbench estimates three black oil properties with five published correlations each. It shows the results side by side and, when a measured value is available, compares every method against it. The aim is to make the differences between correlations easy to see and easy to check.

This is an independent research and learning project by OmahTech. It does not introduce new correlations or new machine learning models. It implements established methods and tests them against published worked examples.

## What it covers

| Property | Symbol | Unit |
|---|---|---|
| Solution gas-oil ratio | Rs | scf/STB |
| Bubble-point pressure | Pb | psia |
| Oil formation volume factor at the bubble point | Bo | bbl/STB |

Each property is estimated with five methods, which gives 15 implementations in total.

- Standing
- Vasquez-Beggs
- Glaso
- Marhoun
- Petrosky-Farshad

The Vasquez-Beggs methods accept optional separator pressure and temperature. When both are given, gas gravity is corrected to the 100 psig reference separator condition. When they are missing, the unadjusted gas gravity is used.

Two modules from Chapter 1 of the same book sit beside the correlations.

- **Oil classification.** Applies the printed limits for ordinary black oil, low-shrinkage oil, volatile oil and near-critical oil to a fluid, shows which limits it passes, and classifies the reservoir as undersaturated, saturated or gas-cap from initial and bubble-point pressure. It can also classify every oil in the public dataset and show how each Bo method performs inside each class.
- **Plus fraction characterization.** Estimates boiling point, critical temperature, critical pressure and critical volume of a heptanes-plus fraction (Riazi and Daubert), the acentric factor (Edmister) and the critical compressibility factor (four methods and the real gas equation).

## Project status

Working now

- A calculation engine in Python for all 15 methods
- A FastAPI service that lists the methods and runs calculations
- A React page for single fluid analysis, with input boxes built from each method's required inputs, an optional measured value, an error column, a reference line and a bar chart
- A script that converts a public PVT dataset into the workbench format
- Dataset analysis, which scores the correlations against the public dataset (Bo) or an uploaded CSV (Rs, Pb or Bo)
- Oil classification and plus fraction characterization from Chapter 1

Still being built

- Method library, showing each method's source and verification record
- About page
- Laboratory PVT analysis from Chapter 3
- Material balance

The original Streamlit prototype (`app.py`, `plots.py`, `compare.py`) is still in the repository.

## Verification

All 15 implementations reproduce the average absolute error (AAE) figures in the worked examples of Chapter 2 of Ahmed's *Reservoir Engineering Handbook*, 5th edition (Examples 2-16 and 2-30).

| Method | Rs AAE (%) | Pb AAE (%) | Bo AAE (%) |
|---|---|---|---|
| Standing | 10.10 | 7.46 | 1.70 |
| Vasquez-Beggs | 4.93 | 4.54 | 2.81 |
| Glaso | 5.82 | 5.04 | 2.77 |
| Marhoun | 12.44 | 7.34 | 1.33 |
| Petrosky-Farshad | 7.84 | 6.74 | 1.79 |

Matching the book shows that the equations are coded as the book describes them. It does not show that a method is accurate for a particular crude oil.

### Differences from the printed text

Two places needed a different treatment to reproduce the book's own answers.

- **Glaso bubble-point pressure (Eq. 2-79).** The printed equation shows the squared term as (pb*)^2. The code uses [log(pb*)]^2, which reproduces the book's answers and follows Glaso's original form.
- **Oil 4 in Example 2-16.** The table prints a temperature of 237 °F. The book's solutions for Standing, Marhoun and Vasquez-Beggs reproduce with 214 °F, so 214 °F is used.

### Chapter 1 modules

Plus fraction characterization is checked against Example 1-1 (M = 150, specific gravity 0.78). `check_chapter1.py` runs the checks.

| Quantity | Book | This tool | Result |
|---|---|---|---|
| Boiling point, Tb (°R) | 825.26 | 825.26 | Matches |
| Critical pressure, pc (psia) | 320.3 | 320.3 | Matches |
| Critical temperature, Tc (°R) | 1139.4 | 1139.8 | Differs by 0.04%, see below |
| Critical volume, Vc (ft³/lb) | 0.06035 | 0.06363 | Does not match |
| Acentric factor | 0.5067 | 0.5067 from the book's printed Tc, pc and Tb | Matches |

Two differences from the printed text.

- **Tc.** The worked line in Example 1-1 prints the constant a as 544.2, while Table 1-4 prints 544.4. With 544.2 the code returns 1139.4, which is the book's answer. The code uses the Table 1-4 value, so it returns 1139.8. This also moves the acentric factor from 0.5067 to 0.5048 when it is calculated from this tool's own Tc.
- **Vc.** The constants printed in Table 1-4 give 0.0636 ft³/lb. The book prints 0.06035. No combination of the printed constants was found that gives 0.06035. Table 1-1 lists 0.0626 to 0.0640 ft³/lb for C8 to C20, so 0.0636 looks consistent with the book's own table. The cause is not identified.

The book prints the Nath equation for the critical compressibility factor (Eq. 1-8) without an acentric factor term. It is coded as 0.2918 − 0.0928ω, in the same form as the other three methods. This reading has not been checked against the original paper.

Oil classification applies the limits on pages 3 to 8 as written. They are typical values, not sharp cut-offs, and they leave gaps. No class covers a gas-oil ratio between 700 and 2,000 scf/STB. Ranges written as "between" are treated as inclusive.

Applied to the public dataset (885 oils after removing duplicates, using measured Rs at the bubble point as the gas-oil ratio), 399 oils fall in ordinary black oil, 61 in low-shrinkage oil, 0 in volatile oil and 5 in near-critical oil. 420 oils (47.5%) fall in no class. 21 oils have a gas-oil ratio of 2,000 scf/STB or more, and none of them has Bo below 2.0, so none meets the printed limits for volatile oil. Near-critical oil could not be confirmed on composition because the dataset has no heptanes-plus content.

## Data

`prepare_dataset.py` converts a public PVT workbook into `data/mendeley_pvt_bo.csv` with the columns `oil`, `region`, `t_f`, `rs_measured`, `api`, `gamma_g` and `bo`. The conversion reads units from each sheet's header and skips any sheet it cannot identify, so nothing is guessed silently. The result has 896 rows from eight sheets.

Known limits of this data

- The workbook has no pressure, bubble-point or separator data, so only Bo can be scored against it.
- Rs is read as scf/STB.
- 22 rows (11 pairs) have measurements identical to a row in another sheet. All 11 pairs involve the Middle East (b) sheet.
- 113 rows, all from the Pakistan sheet, have a gas gravity above 1.5. These are being checked before the data is used for scoring.
- Many of the oils are volatile oils, which black oil correlations are not designed for.
- The North Sea and Middle East samples overlap with the data that Glaso and Marhoun used to fit their correlations, so those methods may look better there than they would on new data.

Confidential operator PVT reports are never included in this repository. They are used only for private testing.

## Credits

- Ahmed, Tarek. *Reservoir Engineering Handbook*, 5th edition. Source of the correlations and the worked examples used for verification.
- Ramirez-Dolores, C. (2025). *PVT Oil Property Data for Oilfields in Africa, Alaska, Malaysia, Middle East, North Sea, Pakistan and United Arab Emirates* (Version 1) [Data set]. Mendeley Data. https://doi.org/10.17632/6mttycsgbw.1. Licensed CC BY 4.0. The dataset was compiled by its authors from published literature, so the individual measurements come from other studies.
- Labedi, R. M. (1982). *PVT Correlations of the African Crudes*. PhD thesis, Colorado School of Mines.

The original correlations were published by Standing, Vasquez and Beggs, Glaso, Marhoun, and Petrosky and Farshad. See the source field of each method in `registry.py` for the equation numbers.

## Running it locally

You need Python 3.10 or later and Node.js.

Backend, from the project folder

```
pip install fastapi uvicorn pandas numpy openpyxl
uvicorn api:app --reload
```

The API runs at http://127.0.0.1:8000. Interactive documentation is at http://127.0.0.1:8000/docs.

Frontend, in a second terminal

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in a browser. The API only accepts requests from that address.

To rebuild the dataset file, place the workbook at `data/PVTData.xlsx` and run `python prepare_dataset.py`.

## Project layout

| Path | Purpose |
|---|---|
| `rs_correlations.py`, `pb_correlations.py`, `bo_correlations.py` | The correlations. Each function takes plain numbers. |
| `registry.py` | Method registry with inputs, units, source and verification status |
| `metrics.py` | Error measures |
| `analyze.py` | Dataset analysis |
| `classification.py` | Oil and reservoir classification from Chapter 1 |
| `plus_fraction.py` | Plus fraction characterization from Chapter 1 |
| `check_chapter1.py` | Checks for the Chapter 1 modules |
| `api.py` | FastAPI service |
| `prepare_dataset.py` | Converts the public workbook into the workbench format |
| `data/` | Worked example data and the converted dataset |
| `frontend/` | React application built with Vite and Recharts |

## Intended use

PVT Workbench is for education and research. Correlations are estimates. Laboratory PVT analysis of a representative fluid sample is preferred for design and reserves decisions, and nothing in this tool replaces it.