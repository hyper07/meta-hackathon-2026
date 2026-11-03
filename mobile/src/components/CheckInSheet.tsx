// "Are you OK?": over every screen, with a countdown ring. Only her voice can answer "I'm OK" (the server
// hears it through the stream), so whoever holds the phone can't dismiss it. The one button gets help.
import { useEffect, useState } from 'react';
import { Modal, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { useTheme } from '../lib/theme';
import { useWatchMe, type CheckIn } from '../lib/watchme';
import { Button } from './ui';

export function CheckInSheet() {
  const { checkin } = useWatchMe();
  // Keyed by the check-in, so each new one starts with a fresh countdown.
  return checkin ? <Sheet key={checkin.startedAt} checkin={checkin} /> : null;
}

function Sheet({ checkin }: { checkin: CheckIn }) {
  const t = useTheme();
  const { answerCheckin } = useWatchMe();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);

  const left = Math.max(0, Math.ceil(checkin.timeout - (now - checkin.startedAt) / 1000));
  const fraction = left / Math.max(1, checkin.timeout);
  const r = 54, c = 2 * Math.PI * r;

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
          <Text style={[styles.hint, { color: t.muted }]}>Say “I’m OK” in your voice. No answer alerts your people.</Text>
          <View style={styles.buttons}>
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
  buttons: { width: '100%', gap: 10, marginTop: 6 },
});
