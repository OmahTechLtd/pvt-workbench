# PVT Workbench

A web tool for comparing published correlations for crude oil properties.

PVT Workbench estimates black oil properties with published correlations, shows the results side by side and, when a measured value is available, compares every method against it. The aim is to make the differences between correlations easy to see and easy to check.

This is an independent research and learning project by OmahTech. It does not introduce new correlations or new machine learning models. It implements established methods and tests them against published worked examples.

## What it covers

### Bubble-point properties

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

### Other oil properties

- **Gravity.** Oil specific gravity and API gravity from density, and solution gas gravity from separator data.
- **Compressibility.** Undersaturated oil compressibility (Vasquez-Beggs, Petrosky-Farshad and McCain), and compressibility below the bubble point.
- **Formation volume factor above the bubble point.** From a known compressibility, Vasquez-Beggs and Petrosky-Farshad.
- **Density.** At the bubble point from Bo or Standing's equation, and above the bubble point from compressibility, Vasquez-Beggs or Petrosky-Farshad.
- **Total formation volume factor.** From its definition, and from Standing, Glaso and Marhoun.
- **Viscosity.** Dead oil (Beal, Beggs-Robinson, Glaso), saturated oil (Chew-Connally, Beggs-Robinson) and undersaturated oil (Beal, Vasquez-Beggs). Each step can start from a measured value or from the result of the step before it.
- **Surface tension.** The Katz form of the Sugden correlation, using parachors.

### Fluid characterization

- **Oil classification.** Applies published limits for ordinary black oil, low-shrinkage oil, volatile oil and near-critical oil, shows which limits a fluid passes, and classifies the reservoir as undersaturated, saturated or gas-cap from initial and bubble-point pressure. It can also classify every oil in the public dataset and show how each Bo method performs inside each class.
- **Phase diagrams.** Schematic pressure-temperature diagrams for the four oil types, with the reservoir temperature line, initial pressure, bubble point and quality lines, plus a liquid-shrinkage chart. They are not computed from a composition and carry no numeric axes.
- **Plus fraction characterization.** Boiling point, critical temperature, critical pressure and critical volume of a heptanes-plus fraction (Riazi and Daubert), the acentric factor (Edmister) and the critical compressibility factor (four methods and the real gas equation).

## Project status

Working now

- A calculation engine in Python for the bubble-point correlations and the other oil properties above
- One FastAPI service (`api.py`) that holds every route
- A page for each feature, including single fluid analysis with a reference line, an error column and a bar chart
- Dataset analysis, which scores the correlations against the public dataset (Bo) or an uploaded CSV (Rs, Pb or Bo)
- A script that converts a public PVT dataset into the workbench format
- Checks against published worked examples, shown on the pages where they apply

Still being built

- Method library, showing each method's source and verification record
- About page
- Laboratory PVT analysis
- Material balance
- Page order and grouping in the sidebar

The original Streamlit prototype (`app.py`, `plots.py`, `compare.py`) is still in the repository.

## Verification

Every implementation is tested against worked examples in Ahmed's *Reservoir Engineering Handbook*, 5th edition. Matching a published example shows that an equation is coded as described. It does not show that a method is accurate for a particular crude oil.

### Bubble-point correlations

All 15 implementations reproduce the average absolute error (AAE) figures in the published examples.

| Method | Rs AAE (%) | Pb AAE (%) | Bo AAE (%) |
|---|---|---|---|
| Standing | 10.10 | 7.46 | 1.70 |
| Vasquez-Beggs | 4.93 | 4.54 | 2.81 |
| Glaso | 5.82 | 5.04 | 2.77 |
| Marhoun | 12.44 | 7.34 | 1.33 |
| Petrosky-Farshad | 7.84 | 6.74 | 1.79 |

Two places needed a different treatment from the printed text.

- **Glaso bubble-point pressure.** The printed equation shows the squared term as (pb*)^2. The code uses [log(pb*)]^2, which reproduces the published answers and follows Glaso's original form.
- **Oil 4 temperature.** The table prints 237 °F. The published solutions for Standing, Marhoun and Vasquez-Beggs reproduce with 214 °F, so 214 °F is used. The compressibility checks below also reproduce with 214 °F, while the viscosity example reproduces with 237 °F. The reason is not identified.

### Gravity, compressibility, formation volume factor, density and total formation volume factor

Gravity, solution gas gravity, compressibility, Bo above the bubble point and Glaso total formation volume factor reproduce the published examples. The page shows each comparison. Where the printed text disagrees with itself, the page shows what was used.

- Pressures in the compressibility example are gauge, so 14.7 psi is added.
- Petrosky-Farshad uses temperature in °F inside the equation. The published parameter of 0.005778 needs that.
- In the density example the row for oil 4 does not match the data given earlier for the same oil (measured 42.25 against 38.92). The other five oils match. The column headings also look shifted by one equation number.
- In the total formation volume factor example, the definition line uses Bg = 0.0001225 where the example's own step gives 0.001225. With 0.001225 the answer is 1.370, not 1.195. Standing's log Bt is printed as 0.0792 and the same numbers give 0.0797.
- The density equation above the bubble point prints an exponent of 0.4096. It is coded as 0.4094 to stay consistent with the matching Bo equation.
- Density above the bubble point has no worked example in the material used, so it is coded from the printed equations and not checked.

### Viscosity and surface tension

The viscosity example is reproduced for all seven methods, with these decisions where the printed text disagrees with itself. The page shows them next to the results.

- Oil 2 dead-oil viscosity is printed as 1.286 cp in the data table and 0.286 cp in the results table. The published averages reproduce only with 1.286.
- Oil 4 undersaturated results reproduce only at 5,000 psi, while the data table lists 6,000 psi.
- The published Beal result for oil 6 (0.945 cp) is below the bubble-point viscosity (0.950 cp), which the equation cannot give. It returns 0.995 cp.
- The Vasquez-Beggs coefficient is printed as 2.6 in the equation and 26 in the worked example. Only 2.6 reproduces the answers.

The surface tension example gives 0.753 dynes/cm and this tool returns 0.752. The example's apparent gas molecular weight is 24.99 but the printed gas composition gives 25.05, which accounts for the difference.

### Fluid characterization

Plus fraction characterization is checked against a published example (M = 150, specific gravity 0.78). `check_classification_fraction.py` runs the checks.

| Quantity | Published | This tool | Result |
|---|---|---|---|
| Boiling point, Tb (°R) | 825.26 | 825.26 | Matches |
| Critical pressure, pc (psia) | 320.3 | 320.3 | Matches |
| Critical temperature, Tc (°R) | 1139.4 | 1139.8 | Differs by 0.04%, see below |
| Critical volume, Vc (ft³/lb) | 0.06035 | 0.06363 | Does not match |
| Acentric factor | 0.5067 | 0.5067 from the published Tc, pc and Tb | Matches |

- **Tc.** The worked line prints the constant a as 544.2, while the constants table prints 544.4. With 544.2 the code returns 1139.4, which is the published answer. The code uses the table value, so it returns 1139.8. This also moves the acentric factor from 0.5067 to 0.5048 when it is calculated from this tool's own Tc.
- **Vc.** The printed constants give 0.0636 ft³/lb. The published answer is 0.06035. No combination of the printed constants was found that gives 0.06035. The source's own property table lists 0.0626 to 0.0640 ft³/lb for C8 to C20, so 0.0636 looks consistent with it. The cause is not identified.
- **Nath equation.** The source prints the equation for the critical compressibility factor without an acentric factor term. It is coded as 0.2918 − 0.0928ω, in the same form as the other three methods. This reading has not been checked against the original paper.

Oil classification applies the published limits as written. They are typical values, not sharp cut-offs, and they leave gaps. No class covers a gas-oil ratio between 700 and 2,000 scf/STB. Ranges written as "between" are treated as inclusive.

Applied to the public dataset (885 oils after removing duplicates, using measured Rs at the bubble point as the gas-oil ratio), 399 oils fall in ordinary black oil, 61 in low-shrinkage oil, 0 in volatile oil and 5 in near-critical oil. 420 oils (47.5%) fall in no class. 21 oils have a gas-oil ratio of 2,000 scf/STB or more, and none of them has Bo below 2.0, so none meets the published limits for volatile oil. Near-critical oil could not be confirmed on composition because the dataset has no heptanes-plus content.

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

- Ahmed, Tarek. *Reservoir Engineering Handbook*, 5th edition. Source of the correlations and the worked examples used for verification so far.
- Ramirez-Dolores, C. (2025). *PVT Oil Property Data for Oilfields in Africa, Alaska, Malaysia, Middle East, North Sea, Pakistan and United Arab Emirates* (Version 1) [Data set]. Mendeley Data. https://doi.org/10.17632/6mttycsgbw.1. Licensed CC BY 4.0. The dataset was compiled by its authors from published literature, so the individual measurements come from other studies.
- Labedi, R. M. (1982). *PVT Correlations of the African Crudes*. PhD thesis, Colorado School of Mines.

The original correlations were published by Standing, Vasquez and Beggs, Glaso, Marhoun, Petrosky and Farshad, Beal, Beggs and Robinson, Chew and Connally, McCain, Katz and others. See the source field of each method for the equation reference.

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
| `api.py` | The FastAPI service. Every route is defined here. |
| `rs_correlations.py`, `pb_correlations.py`, `bo_correlations.py` | The bubble-point correlations. Each function takes plain numbers. |
| `registry.py` | Method registry with inputs, units, source and verification status |
| `metrics.py` | Error measures |
| `analyze.py` | Dataset analysis |
| `oil_properties.py` | Gravity, compressibility, Bo above the bubble point, density and total formation volume factor |
| `viscosity.py` | Dead, saturated and undersaturated oil viscosity |
| `surface_tension.py` | Surface tension of a hydrocarbon mixture |
| `classification.py` | Oil and reservoir classification |
| `plus_fraction.py` | Plus fraction characterization |
| `check_classification_fraction.py` | Checks for classification and plus fraction characterization |
| `prepare_dataset.py` | Converts the public workbook into the workbench format |
| `data/` | Worked example data and the converted dataset |
| `frontend/` | React application built with Vite and Recharts. One page per feature in `src/pages/`. |

## Intended use

PVT Workbench is for education and research. Correlations are estimates. Laboratory PVT analysis of a representative fluid sample is preferred for design and reserves decisions, and nothing in this tool replaces it.