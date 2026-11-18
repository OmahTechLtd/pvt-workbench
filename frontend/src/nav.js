// One list drives both the sidebar and the Home page, so they cannot drift apart.
export const GROUPS = [
  {
    step: "1",
    title: "Describe the fluid",
    blurb: "Know what you are dealing with before choosing a method.",
    items: [
      { to: "/classification", label: "Oil Classification", text: "Black oil, volatile oil or something else, from your gas-oil ratio, gravity and colour." },
      { to: "/fraction", label: "Plus Fraction", text: "Characterise the heavy end of a compositional analysis." },
      { to: "/phase", label: "Phase Diagrams", text: "See where your fluid sits relative to the two-phase envelope." },
    ],
  },
  {
    step: "2",
    title: "Estimate properties",
    blurb: "No lab report yet? Compare published correlations side by side.",
    items: [
      { to: "/properties", label: "Oil Properties", text: "Rs, bubble point and Bo from every method that applies, plus gravity, compressibility, density and two-phase factors. Test the methods on measured data." },
      { to: "/viscosity", label: "Oil Viscosity", text: "Dead, saturated and undersaturated oil viscosity." },
      { to: "/tension", label: "Surface Tension", text: "Oil-gas interfacial tension." },
    ],
  },
  {
    step: "3",
    title: "Check a lab report",
    blurb: "Test a PVT lab report for consistency and put it on the basis you need.",
    items: [
      { to: "/lab", label: "Lab PVT Analysis", text: "Quality-check constant composition, differential and separator tests." },
    ],
  },
  {
    step: "4",
    title: "Use it in the reservoir",
    blurb: "Take the fluid properties into production history.",
    items: [
      { to: "/balance", label: "Material Balance", text: "Oil in place, aquifer influx, gas cap and drive indexes." },
    ],
  },
  {
    title: "Reference",
    blurb: "",
    items: [
      { to: "/library", label: "Method Library", text: "Every method, its source and the range it was built on." },
      { to: "/about", label: "About", text: "Who made this, how it is checked and what it cannot do." },
    ],
  },
];
