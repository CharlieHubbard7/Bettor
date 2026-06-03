import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Opportunities } from "@/pages/Opportunities";
import { TradeLogger } from "@/pages/TradeLogger";
import { TradeJournal } from "@/pages/TradeJournal";
import { Analytics } from "@/pages/Analytics";
import { Settings } from "@/pages/Settings";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "opportunities", element: <Opportunities /> },
      { path: "trades/new", element: <TradeLogger /> },
      { path: "trades", element: <TradeJournal /> },
      { path: "analytics", element: <Analytics /> },
      { path: "settings", element: <Settings /> },
    ],
  },
]);
