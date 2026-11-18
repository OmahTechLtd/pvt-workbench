import { Link } from "react-router-dom";

function Home() {
  return (
    <div>
      <h1>PVT Workbench</h1>
      <p>Estimate. Compare. Evaluate.</p>
      <p>
        Compare established correlations to estimate solution gas-oil ratio,
        bubble-point pressure and oil formation volume factor.
      </p>
      <Link to="/single">Start Single Fluid Analysis</Link>
    </div>
  );
}

export default Home;