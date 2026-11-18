import { Link } from "react-router-dom";

export default function About() {
  return (
    <div>
      <h1>About</h1>
      <p className="subtitle">
        PVT Workbench is an independent project by OmahTech, built by a petroleum engineer for engineers who need to pick a method, defend the choice and move on to the next job.
      </p>

      <section className="card">
        <h2>Who it is for</h2>
        <p>
          Practising and early-career reservoir, production and PVT engineers at operators, service companies and consultancies, especially small and marginal field
          teams who may not have a commercial PVT package. It also works for students learning why one correlation is chosen over another.
        </p>
      </section>

      <section className="card">
        <h2>How it is checked</h2>
        <p>
          Every method is coded from its published source and run against the worked example printed there. The result has to match the printed figure within the
          rounding the source used. Each page ends with a checks table that shows the published value next to this tool's value.
        </p>
        <p>
          Where the printed example disagrees with its own arithmetic, the table says so and explains the difference. Nothing is hidden or adjusted to force a match.
        </p>
      </section>

      <section className="card">
        <h2>What it does not do</h2>
        <ul>
          <li>It does not replace a laboratory PVT study. Correlations estimate; a good sample measured at reservoir conditions is better.</li>
          <li>It does not tune a correlation to your crude. For Bo it ranks the methods on measured oils of similar gravity and says how strong the evidence is. For Rs and bubble point there is no measured data in the workbench yet, so rank them on your own data in Test on data.</li>
          <li>Most correlations were built on crudes from other regions. Compare them with your own measurements before relying on one, using <Link to="/properties?view=data">Test on data</Link>.</li>
          <li>Material balance covers the straight-line methods, drive indexes, saturations and the Tracy form. Aquifer models and gravity-drainage rates are not included.</li>
          <li>It is not a reservoir simulator and it does not do compositional equation-of-state work.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Data and credits</h2>
        <p>
          Methods and worked examples come from Ahmed, T., <em>Reservoir Engineering Handbook</em>, 5th ed., which each page cites by equation and page.
        </p>
        <p>
          The Test on data view uses Ramirez-Dolores, C. (2025), <em>PVT Oil Property Data for Oilfields in Africa, Alaska, Malaysia, Middle East, North Sea, Pakistan and United Arab Emirates</em>,
          Mendeley Data, <a href="https://doi.org/10.17632/6mttycsgbw.1" target="_blank" rel="noreferrer">doi.org/10.17632/6mttycsgbw.1</a>, licensed CC BY 4.0.
          The authors compiled it from published studies, so the individual measurements belong to those studies.
        </p>
      </section>

      <section className="card">
        <h2>Built by OmahTech</h2>
        <p>
          Built in public, one module at a time. Every module is open to checking: if a number looks wrong, the source equation and page are on the screen.
        </p>
      </section>
    </div>
  );
}
