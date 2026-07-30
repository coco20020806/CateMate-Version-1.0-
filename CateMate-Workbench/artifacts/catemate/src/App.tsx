import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { Route, Switch, Router as WouterRouter } from 'wouter';
import { Shell } from '@/components/layout/Shell';

// Pages
import Dashboard from '@/pages/dashboard';
import RunHistory from '@/pages/runs/index';
import NewAnalysis from '@/pages/runs/new';
import RunDetail from '@/pages/runs/detail';
import DeliverablesHub from '@/pages/runs/deliverables';
import DataSources from '@/pages/datasources/index';
import Settings from '@/pages/settings/index';
import Modules from '@/pages/modules/index';

const queryClient = new QueryClient();

function NotFound() {
  return (
    <div className="p-8 text-center text-muted-foreground">
      <h2 className="text-2xl font-bold mb-2 text-foreground">404 - Not Found</h2>
      <p>The page you are looking for does not exist.</p>
    </div>
  );
}

function Router() {
  return (
    <Shell>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/runs" component={RunHistory} />
        <Route path="/runs/new" component={NewAnalysis} />
        <Route path="/runs/:runId" component={RunDetail} />
        <Route path="/runs/:runId/deliver" component={DeliverablesHub} />
        <Route path="/datasources" component={DataSources} />
        <Route path="/settings" component={Settings} />
        <Route path="/modules" component={Modules} />
        <Route component={NotFound} />
      </Switch>
    </Shell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WouterRouter base={import.meta.env.BASE_URL?.replace(/\/$/, '')}>
        <Router />
      </WouterRouter>
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;
