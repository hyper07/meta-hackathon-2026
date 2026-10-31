// Small building blocks shared by the screens.
import { useEffect, useState, type ReactNode } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Switch, Text, TextInput, View, type TextInputProps, type ViewStyle } from 'react-native';
import Svg, { Path } from 'react-native-svg';

import { feel } from '../lib/feel';
import { useTheme } from '../lib/theme';

const AnimatedPath = Animated.createAnimatedComponent(Path);

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  const t = useTheme();
  return <View style={[styles.card, { backgroundColor: t.surface }, style]}>{children}</View>;
}

export function SectionLabel({ children }: { children: ReactNode }) {
  const t = useTheme();
  return <Text style={[styles.section, { color: t.muted }]}>{children}</Text>;
}

export function Hint({ children, style }: { children: ReactNode; style?: object }) {
  const t = useTheme();
  return <Text style={[styles.hint, { color: t.muted }, style]}>{children}</Text>;
}

type Kind = 'primary' | 'secondary' | 'ok' | 'danger' | 'ai' | 'link';

export function Button({ title, onPress, kind = 'primary', disabled, big }: {
  title: string; onPress: () => void; kind?: Kind; disabled?: boolean; big?: boolean;
}) {
  const t = useTheme();
  const bg = { primary: t.blue, secondary: t.fill, ok: t.ok, danger: t.red, ai: t.purple, link: 'transparent' }[kind];
  const fg = kind === 'secondary' ? t.text : kind === 'link' ? t.blue : '#fff';
  return (
    <Pressable accessibilityRole="button" onPress={onPress} onPressIn={() => feel.tap()} disabled={disabled}
      style={({ pressed }) => [styles.button, big && styles.big,
                               { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.85 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] },
                               kind === 'link' && styles.link]}>
      <Text style={[styles.buttonText, big && styles.bigText, { color: fg }]}>{title}</Text>
    </Pressable>
  );
}

export function Field({ label, note, ...props }: TextInputProps & { label: string; note?: string }) {
  const t = useTheme();
  return (
    <View style={styles.field}>
      <Text style={[styles.fieldLabel, { color: t.text }]}>
        {label}{note ? <Text style={{ color: t.muted, fontWeight: '400' }}> ({note})</Text> : null}
      </Text>
      <TextInput placeholderTextColor={t.muted} {...props}
        style={[styles.input, { backgroundColor: t.fill, color: t.text }, props.multiline && styles.multiline]} />
    </View>
  );
}

export function SwitchRow({ label, value, onValueChange }: { label: string; value: boolean; onValueChange: (v: boolean) => void }) {
  const t = useTheme();
  return (
    <View style={[styles.switchRow, { borderTopColor: t.line }]}>
      <Text style={[styles.switchLabel, { color: t.text }]}>{label}</Text>
      <Switch value={value} onValueChange={(v) => { feel.tap(); onValueChange(v); }} trackColor={{ true: t.ok }} />
    </View>
  );
}

export function Segmented<T extends string>({ options, value, onChange, tint }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; tint?: (v: T) => string;
}) {
  const t = useTheme();
  return (
    <View style={[styles.segmented, { backgroundColor: t.fill }]}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable key={o.value} onPress={() => { if (!active) feel.tap(); onChange(o.value); }} accessibilityRole="radio" accessibilityState={{ selected: active }}
            style={[styles.segment, active && { backgroundColor: t.bg }]}>
            <Text style={[styles.segmentText, { color: active ? (tint?.(o.value) ?? t.text) : t.muted }]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Chip({ children, color, bg }: { children: ReactNode; color: string; bg: string }) {
  return <Text style={[styles.chip, { color, backgroundColor: bg }]}>{children}</Text>;
}

/** The semicircle voice-match gauge, 0..1 on the display scale, with the start and stop bars.
 *  The arc and the number glide to each new value. */
const ARC_LEN = Math.PI * 80;

export function Gauge({ value, start = 0.7, strict = 0.9 }: { value: number | null; start?: number; strict?: number }) {
  const t = useTheme();
  const v = Math.max(0, Math.min(1, value ?? 0));
  const [anim] = useState(() => new Animated.Value(0));
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = anim.addListener(({ value: x }) => setShown(x));
    Animated.timing(anim, { toValue: v, duration: 450, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
    return () => anim.removeListener(id);
  }, [v, anim]);
  const color = value == null ? t.muted : v >= strict ? t.ok : v >= start ? t.amber : t.red;
  const dashoffset = anim.interpolate({ inputRange: [0, 1], outputRange: [ARC_LEN, 0] });
  const tick = (x: number) => { const a = Math.PI * (1 - x); return `M${100 + 66 * Math.cos(a)} ${100 - 66 * Math.sin(a)} L${100 + 94 * Math.cos(a)} ${100 - 94 * Math.sin(a)}`; };
  const half = 'M20 100 A80 80 0 0 1 180 100';
  return (
    <View style={{ alignItems: 'center' }}>
      <Svg width={170} height={100} viewBox="0 0 200 118">
        <Path d={half} stroke={t.fillStrong} strokeWidth={13} strokeLinecap="round" fill="none" />
        <AnimatedPath d={half} stroke={color} strokeWidth={13} strokeLinecap="round" fill="none"
          strokeDasharray={`${ARC_LEN}`} strokeDashoffset={dashoffset} />
        <Path d={tick(start)} stroke={t.amber} strokeWidth={3} />
        <Path d={tick(strict)} stroke={t.ok} strokeWidth={3} />
      </Svg>
      <Text style={{ color: t.text, fontSize: 26, fontWeight: '800', marginTop: -44, fontVariant: ['tabular-nums'] }}>
        {value == null ? '–' : `${Math.round(shown * 100)}%`}</Text>
      <Text style={{ color: t.muted, fontSize: 11 }}>match</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 20, padding: 16, marginBottom: 12 },
  section: { fontSize: 13, fontWeight: '600', letterSpacing: 0.8, textTransform: 'uppercase', marginTop: 22, marginBottom: 8, marginHorizontal: 6 },
  hint: { fontSize: 13, lineHeight: 18 },
  button: { borderRadius: 14, paddingVertical: 12, paddingHorizontal: 18, alignItems: 'center', justifyContent: 'center', flexGrow: 1 },
  big: { paddingVertical: 16, borderRadius: 16, width: '100%' },
  link: { paddingHorizontal: 4, flexGrow: 0 },
  buttonText: { fontSize: 16, fontWeight: '600' },
  bigText: { fontSize: 17, fontWeight: '700' },
  field: { marginTop: 12 },
  fieldLabel: { fontSize: 14, fontWeight: '600', marginBottom: 6 },
  input: { borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, fontSize: 16 },
  multiline: { minHeight: 110, textAlignVertical: 'top' },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10,
               borderTopWidth: StyleSheet.hairlineWidth, marginTop: 10 },
  switchLabel: { fontSize: 15, flexShrink: 1, paddingRight: 12 },
  segmented: { flexDirection: 'row', borderRadius: 999, padding: 3, alignSelf: 'center', marginVertical: 10 },
  segment: { borderRadius: 999, paddingVertical: 9, paddingHorizontal: 22 },
  segmentText: { fontWeight: '600', fontSize: 15 },
  chip: { fontSize: 12, fontWeight: '700', paddingVertical: 3, paddingHorizontal: 10, borderRadius: 999, overflow: 'hidden',
          marginRight: 6, marginVertical: 2, alignSelf: 'flex-start' },
});
