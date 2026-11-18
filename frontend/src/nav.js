// One list drives the sidebar and the Home page, so they cannot drift apart.
export const GROUPS = [
  {
    title: "Describe the fluid",
    items: [
      { to: "/classification", label: "Oil Classification", text: "Black oil, volatile oil or something else, from published limits" },
      { to: "/fraction", label: "Plus Fraction", text: "Critical properties of the heptanes-plus fraction" },
      { to: "/phase", label: "Phase Diagrams", text: "Pressure and temperature diagrams for the four oil types" },
    ],
  },
  {
    title: "Oil properties",
    items: [
      { to: "/properties/gravity", label: "Oil gravity", text: "Specific gravity and API gravity from stock-tank density" },
      { to: "/properties/gasgravity", label: "Solution gas gravity", text: "Gas gravity from separator data" },
      { to: "/properties/rs", label: "Gas solubility, Rs", text: "Compare the published correlations, or test them on measured data" },
      { to: "/properties/pb", label: "Bubble-point pressure, Pb", text: "Compare the published correlations, or test them on measured data" },
      { to: "/properties/bo", label: "Formation volume factor, Bo", text: "Saturated and undersaturated oil, plus a test on measured data" },
      { to: "/properties/co", label: "Compressibility", text: "Isothermal compressibility above and below the bubble point" },
      { to: "/properties/rho", label: "Oil density", text: "Density at and above the bubble point" },
      { to: "/properties/bt", label: "Total formation volume factor", text: "Two-phase factor below the bubble point" },
      { to: "/properties/viscosity", label: "Viscosity", text: "Dead, saturated and undersaturated oil viscosity" },
      { to: "/properties/tension", label: "Surface tension", text: "Oil and gas interfacial tension" },
    ],
  },
  {
    title: "Check a lab report",
    items: [
      { to: "/lab", label: "Lab PVT Analysis", text: "Consistency checks, separator tests and adjustment to a new bubble point" },
    ],
  },
  {
    title: "Use it in the reservoir",
    items: [
      { to: "/balance", label: "Material Balance", text: "Oil in place, water influx, gas cap and drive indexes" },
    ],
  },
  {
    title: "Reference",
    items: [
      { to: "/library", label: "Method Library", text: "Every method, its source and what it needs" },
      { to: "/about", label: "About", text: "Who made this, how it is checked and what it cannot do" },
    ],
  },
];
