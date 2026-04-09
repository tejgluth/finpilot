import { useSearchParams } from "react-router-dom";
import SetupWizard from "../components/setup/SetupWizard";

export default function SetupPage() {
  const [searchParams] = useSearchParams();
  return <SetupWizard focusService={searchParams.get("service")} />;
}
