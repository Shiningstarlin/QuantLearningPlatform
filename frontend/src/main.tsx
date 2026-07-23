import React from "react";
import ReactDOM from "react-dom/client";
import { Navigate, RouterProvider, createBrowserRouter } from "react-router-dom";

import { AppLayout } from "./shell/AppLayout";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AssetsPage } from "./pages/AssetsPage";
import { BacktestDetailPage } from "./pages/BacktestDetailPage";
import { BacktestComparePage } from "./pages/BacktestComparePage";
import { BacktestsPage } from "./pages/BacktestsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { LogsPage } from "./pages/LogsPage";
import { MarketBoardPage } from "./pages/MarketBoardPage";
import { MarketAssetDetailPage } from "./pages/MarketAssetDetailPage";
import { NewBacktestPage } from "./pages/NewBacktestPage";
import { NewTaskPage } from "./pages/NewTaskPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TaskDetailPage } from "./pages/TaskDetailPage";
import { TasksPage } from "./pages/TasksPage";
import "./styles.css";

const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <AppLayout />,
    children: [
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/market-board", element: <MarketBoardPage /> },
      { path: "/market-board/:assetId", element: <MarketAssetDetailPage /> },
      { path: "/tasks", element: <TasksPage /> },
      { path: "/tasks/new", element: <NewTaskPage /> },
      { path: "/tasks/:taskId", element: <TaskDetailPage /> },
      { path: "/tasks/:taskId/assets", element: <AssetsPage /> },
      { path: "/tasks/:taskId/logs", element: <LogsPage /> },
      { path: "/tasks/:taskId/analytics", element: <AnalyticsPage /> },
      { path: "/backtests", element: <BacktestsPage /> },
      { path: "/backtests/new", element: <NewBacktestPage /> },
      { path: "/backtests/compare", element: <BacktestComparePage /> },
      { path: "/backtests/:backtestId", element: <BacktestDetailPage /> },
      { path: "/settings", element: <SettingsPage /> }
    ]
  }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
