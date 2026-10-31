// The toast that slides up over the tab bar when the voice lock decides something, a review is ready,
// or the connection comes back. Tap to dismiss; it leaves on its own after a few seconds.
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import Animated, { FadeOutDown, SlideInDown } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTheme } from '../lib/theme';
import { useWatchMe } from '../lib/watchme';

export function ToastHost() {
  const t = useTheme();
  const { toast } = useWatchMe();
  const insets = useSafeAreaInsets();
  const [hiddenId, setHiddenId] = useState(0);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setHiddenId(toast.id), 4500);
    return () => clearTimeout(id);
  }, [toast]);

  if (!toast || toast.id === hiddenId) return null;
  const bg = toast.kind === 'ok' ? t.ok : toast.kind === 'bad' ? t.red : t.blue;
  const icon = toast.kind === 'ok' ? '✓' : toast.kind === 'bad' ? '🔒' : '📝';
  return (
    <Animated.View key={toast.id} entering={SlideInDown.springify().damping(16)} exiting={FadeOutDown}
      style={[styles.wrap, { bottom: insets.bottom + 70 }]}>
      <Pressable onPress={() => setHiddenId(toast.id)} style={[styles.toast, { backgroundColor: bg }]} accessibilityRole="alert">
        <Text style={styles.icon}>{icon}</Text>
        <Text style={styles.text}><Text style={{ fontWeight: '800' }}>{toast.title}</Text>{toast.text ? `. ${toast.text}` : ''}</Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 16, right: 16 },
  toast: { flexDirection: 'row', alignItems: 'center', gap: 10, borderRadius: 18, paddingVertical: 14, paddingHorizontal: 16,
           shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 8 },
  icon: { fontSize: 22, color: '#fff' },
  text: { color: '#fff', fontSize: 15, flex: 1 },
});
