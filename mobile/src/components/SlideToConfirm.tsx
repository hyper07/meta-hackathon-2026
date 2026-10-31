// Slide to confirm: a deliberate gesture, so "I'm OK" can't be dismissed by a stray tap or a pocket.
import { useEffect, useRef, useState } from 'react';
import { Animated, PanResponder, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import { feel } from '../lib/feel';
import { useTheme } from '../lib/theme';

const KNOB = 56;

export function SlideToConfirm({ label, color, onConfirm }: { label: string; color: string; onConfirm: () => void }) {
  const t = useTheme();
  const [x] = useState(() => new Animated.Value(0));
  const [width, setWidth] = useState(0);
  const max = Math.max(1, width - KNOB - 8);
  // The responder is made once; these always point at the latest size and callback.
  const maxRef = useRef(max);
  const onConfirmRef = useRef(onConfirm);
  useEffect(() => { maxRef.current = max; onConfirmRef.current = onConfirm; }, [max, onConfirm]);

  // eslint-disable-next-line react-hooks/refs -- the handlers read the refs when a gesture happens, not during render
  const [pan] = useState(() => PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: () => feel.tap(),
    onPanResponderMove: (_, g) => x.setValue(Math.max(0, Math.min(g.dx, maxRef.current))),
    onPanResponderRelease: (_, g) => {
      if (g.dx >= maxRef.current * 0.85) {
        feel.commit();
        Animated.timing(x, { toValue: maxRef.current, duration: 120, useNativeDriver: true }).start(() => {
          onConfirmRef.current();
          x.setValue(0);
        });
      } else {
        Animated.spring(x, { toValue: 0, useNativeDriver: true, friction: 6 }).start();
      }
    },
  }));
  const fade = x.interpolate({ inputRange: [0, max * 0.6], outputRange: [1, 0], extrapolate: 'clamp' });
  return (
    <View onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}
      style={[styles.track, { backgroundColor: t.fill }]} accessibilityRole="adjustable" accessibilityLabel={label}
      accessibilityActions={[{ name: 'activate' }]} onAccessibilityAction={() => onConfirm()}>
      <Animated.Text style={[styles.label, { color: t.text, opacity: fade }]}>{label}  ›</Animated.Text>
      <Animated.View {...pan.panHandlers} style={[styles.knob, { backgroundColor: color, transform: [{ translateX: x }] }]}>
        <Text style={styles.arrow}>→</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  track: { height: KNOB + 8, borderRadius: 999, justifyContent: 'center', padding: 4, width: '100%' },
  label: { position: 'absolute', alignSelf: 'center', fontSize: 17, fontWeight: '700' },
  knob: { width: KNOB, height: KNOB, borderRadius: KNOB / 2, alignItems: 'center', justifyContent: 'center' },
  arrow: { color: '#fff', fontSize: 24, fontWeight: '800' },
});
