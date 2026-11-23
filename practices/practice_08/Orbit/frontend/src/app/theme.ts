import { createTheme, type CSSVariablesResolver } from '@mantine/core';

export const theme = createTheme({
  fontFamily: 'Inter Variable, Inter, system-ui, sans-serif',
  headings: { fontFamily: 'PT Serif, Georgia, serif', fontWeight: '400' },
  primaryColor: 'indigo',
  primaryShade: { light: 8, dark: 4 },
  autoContrast: true,
  defaultRadius: 'sm',
  colors: {
    indigo: ['#f1f6f3', '#dfeae3', '#bed2c6', '#9bbbaa', '#86a996', '#708f7e', '#537462', '#40634f', '#304e40', '#20392d'],
  },
});

const light = {
  '--paper': '#f3f3ef', '--surface': '#ffffff', '--panel-alt': '#e9edeb',
  '--line': '#c6ccc7', '--ink': '#192122', '--muted': '#54615f', '--pine': '#354f46',
  '--selected': '#21342c', '--selected-ink': '#ffffff', '--copper': '#69408b',
  '--event': '#293b78', '--event-bg': '#e6e9fc', '--event-mark': '#5065ac',
  '--deadline': '#843c2c', '--deadline-bg': '#f8e0d9', '--deadline-mark': '#ac5943',
  '--birthday': '#713963', '--birthday-bg': '#f3e1f0', '--birthday-mark': '#a25992',
  '--step': '#15556a', '--step-bg': '#daf0f4', '--step-mark': '#28788b',
  '--lesson': '#243d32', '--lesson-bg': '#e1e9e5',
  '--mantine-color-body': '#f3f3ef', '--mantine-color-text': '#192122',
};
const dark = {
  '--paper': '#161c1c', '--surface': '#202928', '--panel-alt': '#29332e',
  '--line': '#485451', '--ink': '#f6f1e7', '--muted': '#b2c0ba', '--pine': '#c0decc',
  '--selected': '#c8ddd1', '--selected-ink': '#21342c', '--copper': '#dec3fa',
  '--event': '#dce1ff', '--event-bg': '#2e3d70', '--event-mark': '#9baaf2',
  '--deadline': '#ffe1d6', '--deadline-bg': '#624237', '--deadline-mark': '#e5a590',
  '--birthday': '#ffe0f6', '--birthday-bg': '#55334f', '--birthday-mark': '#e7a0d5',
  '--step': '#d8fbff', '--step-bg': '#274939', '--step-mark': '#8bd6e2',
  '--lesson': '#d4eadc', '--lesson-bg': '#303f3a',
  '--mantine-color-body': '#161c1c', '--mantine-color-text': '#f6f1e7',
};

export const calendarVariables: CSSVariablesResolver = () => ({ variables: {}, light, dark });
