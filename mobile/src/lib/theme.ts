// The web page's palette (app/static/app.css): one accent blue, black or white backgrounds.
import { useColorScheme } from 'react-native';

const light = {
  bg: '#ffffff', surface: '#f2f2f7', fill: '#e9e9ee', fillStrong: '#d9d9e0', line: 'rgba(0,0,0,0.08)',
  text: '#0a0a0a', muted: '#6e6e73',
  blue: '#0866ff', ok: '#31a24c', red: '#ff3b30', purple: '#8a4dff', amber: '#ff9f0a',
  tintRed: '#ffe9e7', tintPurple: '#f1e9ff', tintAmber: '#fff3dc', tintOk: '#e6f6ea', tintBlue: '#e8f0ff',
};
const dark: typeof light = {
  bg: '#000000', surface: '#141416', fill: '#1f1f23', fillStrong: '#2c2c31', line: 'rgba(255,255,255,0.08)',
  text: '#f5f5f7', muted: '#98989f',
  blue: '#3d8bff', ok: '#34c759', red: '#ff453a', purple: '#a97dff', amber: '#ffb340',
  tintRed: '#3a1512', tintPurple: '#261a3f', tintAmber: '#3a2a0c', tintOk: '#10301a', tintBlue: '#10233f',
};

export type Theme = typeof light;

export function useTheme(): Theme {
  return useColorScheme() === 'dark' ? dark : light;
}

/** The AI gradient, only on the live orb. */
export const GRADIENT = {
  idle: ['#0ab8ff', '#2e6bf0', '#9c4df4', '#ff6ab1'],
  watching: ['#ff3b30', '#ff8a65', '#ff2d55', '#ff3b30'],
  noticing: ['#8a4dff', '#c7a6ff', '#6e3cff', '#8a4dff'],
};

export const levelColor = (t: Theme, level?: string) =>
  level === 'urgent' ? t.red : level === 'concern' ? t.amber : level === 'watch' ? '#ffcc00' : t.fillStrong;
