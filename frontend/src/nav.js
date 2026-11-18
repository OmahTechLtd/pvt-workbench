// One list drives the sidebar and the Home page, so they cannot drift apart.
// An item with `children` shows them as indented links under it. A child's `view` is the ?view= value of the Oil Properties page.
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
    title: "Estimate properties",
    items: [
      {
        to: "/properties",
        label: "Oil Properties",
        text: "Rs, bubble point and Bo from every method, plus gravity, compressibility and density",
        children: [
          { to: "/properties", view: "compare", label: "Compare methods", text: "Rs, bubble point and Bo from every published correlation that applies" },
          { to: "/properties?view=other", view: "other", label: "Other properties", text: "Gravity, compressibility, density and two-phase factor" },
          { to: "/properties?view=data", view: "data", label: "Test on data", text: "Score the methods on measured oils or your own CSV" },
        ],
      },
      { to: "/viscosity", label: "Oil Viscosity", text: "Dead, saturated and undersaturated oil viscosity" },
      { to: "/tension", label: "Surface Tension", text: "Oil and gas interfacial tension" },
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
