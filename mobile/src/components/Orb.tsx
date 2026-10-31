// The live orb: a gradient ring that turns while listening, red while watching, purple in Notice mode.
// It breathes with the room's loudness, and holding it fills a ring that starts listening when it closes.
import { useEffect, useRef, useState } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Stop } from 'react-native-svg';

import { feel } from '../lib/feel';
import { GRADIENT, useTheme } from '../lib/theme';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);
const HOLD_MS = 700;
const SIZE = 240;
const HOLD_R = SIZE / 2 - 14;
const HOLD_LEN = 2 * Math.PI * HOLD_R;

type Props = {
  state: 'off' | 'ready' | 'watching' | 'noticing';
  level: number;
  label: string;
  hint: string;
  /** Called when a hold reaches the end; omit to make the orb not holdable. */
  onHold?: () => void;
};

export function Orb({ state, level, label, hint, onHold }: Props) {
  const t = useTheme();
  const [spin] = useState(() => new Animated.Value(0));
  const [breath] = useState(() => new Animated.Value(1));
  const [hold] = useState(() => new Animated.Value(0));
  const holdAnim = useRef<Animated.CompositeAnimation | null>(null);
  const live = state !== 'off';
  const colors = state === 'watching' ? GRADIENT.watching : state === 'noticing' ? GRADIENT.noticing : GRADIENT.idle;

  useEffect(() => {
    if (!live) { spin.stopAnimation(); return; }
    const period = state === 'watching' ? 2800 : state === 'noticing' ? 5000 : 7000;
    const loop = Animated.loop(Animated.timing(spin, { toValue: 1, duration: period, easing: Easing.linear, useNativeDriver: true }));
    spin.setValue(0);
    loop.start();
    return () => loop.stop();
  }, [live, state, spin]);

  // Louder room, slightly bigger orb: a spring, so it swells and settles rather than jitters.
  useEffect(() => {
    Animated.spring(breath, { toValue: 1 + (live ? level : 0) * 0.06, friction: 6, tension: 80, useNativeDriver: true }).start();
  }, [level, live, breath]);

  const pressIn = () => {
    if (!onHold) return;
    feel.tap();
    holdAnim.current = Animated.timing(hold, { toValue: 1, duration: HOLD_MS, easing: Easing.out(Easing.quad), useNativeDriver: false });
    holdAnim.current.start(({ finished }) => {
      if (!finished) return;
      feel.commit();
      onHold();
      Animated.timing(hold, { toValue: 0, duration: 250, useNativeDriver: false }).start();
    });
  };
  const pressOut = () => {
    holdAnim.current?.stop();
    Animated.timing(hold, { toValue: 0, duration: 200, useNativeDriver: false }).start();
  };

  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const dashoffset = hold.interpolate({ inputRange: [0, 1], outputRange: [HOLD_LEN, 0] });
  const glow = 0.08 + level * 0.5;

  return (
    <Pressable onPressIn={pressIn} onPressOut={pressOut} disabled={!onHold} accessibilityRole="button"
      accessibilityLabel={onHold ? `${label}. Press and hold to start listening.` : label}>
      <Animated.View style={[styles.wrap, { transform: [{ scale: breath }] }]}>
        <View style={[StyleSheet.absoluteFill, styles.glow, { backgroundColor: colors[1], opacity: live ? glow : 0.05 }]} />
        <Animated.View style={[StyleSheet.absoluteFill, { transform: [{ rotate }], opacity: live ? 1 : 0.3 }]}>
          <Svg width={SIZE} height={SIZE}>
            <Defs>
              <LinearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
                {colors.map((c, i) => <Stop key={i} offset={i / (colors.length - 1)} stopColor={c} />)}
              </LinearGradient>
            </Defs>
            <Circle cx={SIZE / 2} cy={SIZE / 2} r={SIZE / 2 - 5} stroke="url(#ring)" strokeWidth={5} fill="none" />
          </Svg>
        </Animated.View>
        <View style={[styles.core, { backgroundColor: t.bg }]}>
          <Text style={[styles.label, { color: t.text }]}>{label}</Text>
          <Text style={[styles.hint, { color: t.muted }]}>{hint}</Text>
        </View>
        {onHold && (
          <Svg width={SIZE} height={SIZE} style={[StyleSheet.absoluteFill, { transform: [{ rotate: '-90deg' }] }]} pointerEvents="none">
            <AnimatedCircle cx={SIZE / 2} cy={SIZE / 2} r={HOLD_R} stroke={t.blue} strokeWidth={4} fill="none" strokeLinecap="round"
              strokeDasharray={`${HOLD_LEN}`} strokeDashoffset={dashoffset} />
          </Svg>
        )}
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { width: SIZE, height: SIZE, alignSelf: 'center', alignItems: 'center', justifyContent: 'center', marginVertical: 8 },
  glow: { borderRadius: 999, transform: [{ scale: 0.86 }] },
  core: { position: 'absolute', top: 14, left: 14, right: 14, bottom: 14, borderRadius: 999,
          alignItems: 'center', justifyContent: 'center', padding: 24 },
  label: { fontSize: 34, fontWeight: '800', letterSpacing: -0.5 },
  hint: { fontSize: 14, textAlign: 'center', marginTop: 4 },
});
