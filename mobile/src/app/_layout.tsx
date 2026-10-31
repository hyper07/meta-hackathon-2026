import { NativeTabs } from 'expo-router/native-tabs';
import { StatusBar } from 'expo-status-bar';

import { CheckInSheet } from '../components/CheckInSheet';
import { ToastHost } from '../components/ToastHost';
import { WatchMeProvider } from '../lib/watchme';

export default function Layout() {
  return (
    <WatchMeProvider>
      <StatusBar style="auto" />
      <NativeTabs>
        <NativeTabs.Trigger name="index">
          <NativeTabs.Trigger.Icon sf="shield.lefthalf.filled" md="shield" />
          <NativeTabs.Trigger.Label>Watch</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="review">
          <NativeTabs.Trigger.Icon sf="clock" md="history" />
          <NativeTabs.Trigger.Label>Review</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="notice">
          <NativeTabs.Trigger.Icon sf="doc.text" md="description" />
          <NativeTabs.Trigger.Label>Notice</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="setup">
          <NativeTabs.Trigger.Icon sf="gearshape" md="settings" />
          <NativeTabs.Trigger.Label>Setup</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
      </NativeTabs>
      <ToastHost />
      <CheckInSheet />
    </WatchMeProvider>
  );
}
