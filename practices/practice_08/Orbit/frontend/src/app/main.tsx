import '@mantine/core/styles.css';
import '@fontsource-variable/inter';
import '@fontsource/pt-serif/cyrillic-400.css';
import '@fontsource/pt-serif/latin-400.css';
import './styles.css';
import { MantineProvider } from '@mantine/core';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { CalendarPage } from '../features/calendar/CalendarPage';
import { PlanDetailPage } from '../features/plans/PlanDetailPage';
import { PlansPage } from '../features/plans/PlansPage';
import { calendarVariables, theme } from './theme';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider theme={theme} cssVariablesResolver={calendarVariables} defaultColorScheme="light">
      <BrowserRouter>
        <Routes>
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/plans" element={<PlansPage />} />
          <Route path="/plans/:id" element={<PlanDetailPage />} />
          <Route path="*" element={<Navigate replace to="/calendar" />} />
        </Routes>
      </BrowserRouter>
    </MantineProvider>
  </StrictMode>,
);
