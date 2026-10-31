// "Are you OK?": over every screen, with a countdown ring. She can answer by voice ("I'm OK"), which the
// server hears through the stream, or by sliding. Sliding to "I'm OK" asks for the PIN, so someone holding
// her phone can't dismiss it; "Get help now" needs nothing.
import { useEffect, useState } from 'react';
import { Modal, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { useTheme } from '../lib/theme';
import { useWatchMe, type CheckIn } from '../lib/watchme';
import { SlideToConfirm } from './SlideToConfirm';
import { Button } from './ui';

export function CheckInSheet() {
  const { checkin } = useWatchMe();
  // Keyed by the check-in, so each new one starts with a fresh countdown and no PIN typed.
  return checkin ? <Sheet key={checkin.startedAt} checkin={checkin} /> : null;
}

function Sheet({ checkin }: { checkin: CheckIn }) {
  const t = useTheme();
  const { answerCheckin, profile } = useWatchMe();
  const [now, setNow] = useState(() => Date.now());
  const [askPin, setAskPin] = useState(false);
  const [pin, setPin] = useState('');

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const left = Math.max(0, Math.ceil(checkin.timeout - (now - checkin.startedAt) / 1000));
  const fraction = left / Math.max(1, checkin.timeout);
  const r = 54, c = 2 * Math.PI * r;

  const ok = () => {
    if (profile.has_pin && !askPin) { setAskPin(true); return; }
    answerCheckin(true, pin || undefined);
  };

  return (
    <Modal transparent animationType="fade" visible>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: t.bg }]}>
          <Text style={[styles.q, { color: t.text }]}>Are you OK?</Text>
          {!!checkin.reason && <Text style={[styles.why, { color: t.muted }]}>{checkin.reason}</Text>}
          <View style={styles.count}>
            <Svg width={150} height={150} viewBox="0 0 120 120" style={{ transform: [{ rotate: '-90deg' }] }}>
              <Circle cx={60} cy={60} r={r} stroke={t.fill} strokeWidth={8} fill="none" />
              <Circle cx={60} cy={60} r={r} stroke={t.red} strokeWidth={8} fill="none" strokeLinecap="round"
                strokeDasharray={`${c}`} strokeDashoffset={c * (1 - fraction)} />
            </Svg>
            <Text style={[styles.number, { color: t.red }]}>{left}</Text>
          </View>
          <Text style={[styles.hint, { color: t.muted }]}>Say “I’m OK”, or slide. No answer alerts your people.</Text>
          {askPin && (
            <TextInput value={pin} onChangeText={setPin} placeholder="PIN" placeholderTextColor={t.muted} keyboardType="number-pad"
              secureTextEntry maxLength={8} autoFocus style={[styles.pin, { backgroundColor: t.fill, color: t.text }]} />
          )}
          <View style={styles.buttons}>
            {askPin ? <Button big kind="ok" title="Confirm I’m OK" onPress={ok} />
                    : <SlideToConfirm label="Slide: I’m OK" color={t.ok} onConfirm={ok} />}
            <Button big kind="danger" title="Get help now" onPress={() => answerCheckin(false)} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', alignItems: 'center', justifyContent: 'center', padding: 16 },
  sheet: { width: '100%', maxWidth: 380, borderRadius: 28, padding: 24, alignItems: 'center' },
  q: { fontSize: 34, fontWeight: '800', letterSpacing: -0.5 },
  why: { fontSize: 14, textAlign: 'center', marginTop: 6 },
  count: { width: 150, height: 150, marginVertical: 12, alignItems: 'center', justifyContent: 'center' },
  number: { position: 'absolute', fontSize: 56, fontWeight: '800', fontVariant: ['tabular-nums'] },
  hint: { fontSize: 13, textAlign: 'center', marginBottom: 8 },
  pin: { width: '100%', textAlign: 'center', fontSize: 26, letterSpacing: 8, borderRadius: 12, paddingVertical: 10, marginVertical: 6 },
  buttons: { width: '100%', gap: 10, marginTop: 6 },
});
