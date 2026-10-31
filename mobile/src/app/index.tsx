// Watch: the orb, Emergency or Notice, start and stop listening, the voice lock, and what it heard.
import { useEffect, useState } from 'react';
import { Animated, Modal, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Reanimated, { FadeInDown, LinearTransition } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Orb } from '../components/Orb';
import { Button, Card, Gauge, Hint, Segmented } from '../components/ui';
import { levelColor, useTheme } from '../lib/theme';
import { useWatchMe, type Line } from '../lib/watchme';

const MODE_HINTS = {
  watch: 'Asks “Are you OK?” and alerts your people if you can’t answer.',
  notice: 'For class or work. No check-ins, no alerts; a review when you stop.',
};

export default function Watch() {
  const t = useTheme();
  const w = useWatchMe();
  const [pinFor, setPinFor] = useState<'start' | 'stop' | null>(null);
  const [error, setError] = useState('');
  const [shake] = useState(() => new Animated.Value(0));

  // Another voice was refused: the voice lock shakes, like a wrong passcode.
  useEffect(() => {
    if (!w.refusedAt) return;
    shake.setValue(0);
    Animated.sequence([10, -10, 8, -8, 0].map((v) => Animated.timing(shake, { toValue: v, duration: 60, useNativeDriver: true }))).start();
  }, [w.refusedAt, shake]);

  const watching = w.state === 'watching';
  const noticing = watching && w.mode === 'notice';
  const orbState = noticing ? 'noticing' : watching ? 'watching' : w.listening ? 'ready' : 'off';
  const label = noticing ? 'Noticing' : watching ? 'Watching' : w.listening ? 'Ready' : 'Off';
  const hint = noticing ? 'Say “stop watching” for your review.'
    : watching ? 'Only your voice can say “stop watching”.'
    : w.listening ? 'Say “Watch me”' : 'Start listening, then say “Watch me”';

  const toggle = async () => {
    setError('');
    try {
      if (w.listening) await w.stopListening();
      else await w.startListening();
    }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg }} edges={['top']}>
      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.header}>
          <View style={[styles.dot, { backgroundColor: watching ? (noticing ? t.purple : t.red) : w.listening ? t.blue : t.fillStrong }]} />
          <Text style={[styles.brand, { color: t.text }]}>Watch Me</Text>
          {!w.connected && <Text style={[styles.conn, { color: t.muted }]}>{w.serverUrl ? 'connecting…' : 'no server set'}</Text>}
        </View>

        {w.offline && (
          <View style={[styles.banner, { backgroundColor: t.tintAmber, borderLeftColor: t.amber }]}>
            <Text style={{ color: t.text }}><Text style={{ fontWeight: '700' }}>Offline.</Text> Still listening and checking in;
              everything is saved. {w.pending ? `${w.pending} moment${w.pending === 1 ? '' : 's'} waiting for a connection.` : ''}</Text>
          </View>
        )}

        <Orb state={orbState} level={w.listening ? w.level : 0} label={label}
          hint={!w.listening && w.connected ? 'Hold to start listening' : hint}
          onHold={!w.listening && !watching && w.connected ? toggle : undefined} />

        <View style={styles.pills}>
          {watching && w.profile.enrolled && <Text style={[styles.pill, { backgroundColor: t.tintAmber, color: t.amber }]}>🔒 Locked to your voice</Text>}
        </View>

        {!watching && (
          <>
            <Segmented options={[{ value: 'watch', label: 'Emergency' }, { value: 'notice', label: 'Notice' }]}
              value={w.mode} onChange={w.setMode} tint={(v) => (v === 'watch' ? t.red : t.purple)} />
            <Hint style={{ textAlign: 'center', marginBottom: 12 }}>{MODE_HINTS[w.mode]}</Hint>
          </>
        )}
        {!watching && <Button big title={w.listening ? 'Stop listening' : 'Start listening'} onPress={toggle} disabled={!w.connected} />}
        <Button kind="link" title={watching ? 'Stop with PIN' : 'Use PIN instead'} onPress={() => setPinFor(watching ? 'stop' : 'start')} />
        {!!error && <Hint style={{ color: t.red, textAlign: 'center' }}>{error}</Hint>}
        {!w.profile.enrolled && w.connected && <Hint style={{ textAlign: 'center' }}>Record your voice in Setup first, so only you can start and stop Watch Me.</Hint>}

        {!!w.banner && (
          <View style={[styles.banner, { backgroundColor: t.surface, borderLeftColor: t.blue }]}>
            <Text style={{ color: t.text }} onPress={w.dismissBanner}>{w.banner}</Text>
          </View>
        )}

        {w.listening && w.profile.enrolled && (
          <Animated.View style={{ transform: [{ translateX: shake }] }}><Card>
            <Text style={[styles.cardTitle, { color: t.text }]}>Voice lock <Text style={{ color: t.muted, fontWeight: '400', fontSize: 12 }}>· only your voice can stop it</Text></Text>
            <Gauge value={w.voice?.match ?? null} />
            <Text style={{ color: t.muted, textAlign: 'center', marginTop: 4 }}>
              {!w.voice ? 'Waiting for a voice' : w.voice.strict ? 'You · verified' : w.voice.owner ? 'Probably you' : 'Someone else'}
            </Text>
          </Card></Animated.View>
        )}

        {w.alert && (
          <Reanimated.View entering={FadeInDown.springify()} style={[styles.alert, { backgroundColor: t.tintRed }]}>
            <Text style={{ color: t.red, fontWeight: '700' }}>Alert sent to {w.alert.contacts} contact{w.alert.contacts === 1 ? '' : 's'}{w.alert.sent_to ? ` · ${w.alert.sent_to}` : ''}</Text>
            <Text style={{ color: t.text, marginVertical: 6 }}>{w.alert.message}</Text>
            {(w.alert.results ?? []).map((r: { to: string; channel: string; result: string }, i: number) => (
              <Hint key={i}>{r.to} · {r.channel}: {r.result}</Hint>
            ))}
          </Reanimated.View>
        )}

        {watching && <Text style={[styles.section, { color: t.muted }]}>WHAT IT HEARD</Text>}
        {watching && w.lines.map((l) => (
          <Reanimated.View key={l.key} entering={FadeInDown.duration(280)} layout={LinearTransition.duration(220)}>
            <LineRow line={l} />
          </Reanimated.View>
        ))}
      </ScrollView>
      <PinPrompt visible={!!pinFor} title={pinFor === 'stop' ? 'PIN to stop' : 'PIN to start'}
        onCancel={() => setPinFor(null)}
        onSubmit={(pin) => { w.send({ type: pinFor === 'stop' ? 'stop_pin' : 'start_pin', pin }); setPinFor(null); }} />
    </SafeAreaView>
  );
}

function LineRow({ line }: { line: Line }) {
  const t = useTheme();
  if (line.type === 'decision' || line.type === 'noted') {
    const what = line.type === 'noted' ? 'Marked for your review' : line.action === 'ask' ? (line.urgent ? 'Urgent check-in' : 'Check-in') : line.action;
    return <Hint style={{ paddingVertical: 6, paddingHorizontal: 12 }}>◆ {what}{line.reason || line.why ? `: ${line.reason ?? line.why}` : ''}</Hint>;
  }
  const who = line.speaker === 'owner' ? 'You' : line.speaker === 'other' ? 'Someone else' : 'Voice';
  const marked = line.level && line.level !== 'none';
  return (
    <View style={[styles.seg, { backgroundColor: t.surface }]}>
      <View style={[styles.bar, { backgroundColor: levelColor(t, line.level) }]} />
      <View style={{ flex: 1 }}>
        <View style={styles.meta}>
          <Text style={{ fontWeight: '700', fontSize: 12, color: line.speaker === 'owner' ? t.blue : t.text }}>{who}</Text>
          <Text style={{ fontSize: 12, color: t.muted }}>{new Date(line.t * 1000).toLocaleTimeString()}</Text>
          {marked && <Text style={[styles.score, { backgroundColor: t.fill, color: t.text }]}>{Number(line.score ?? 0).toFixed(2)}</Text>}
        </View>
        <Text style={{ color: t.text, fontSize: 16, marginTop: 2 }}>{line.text}</Text>
        {!!line.reason && <Hint style={{ marginTop: 3 }}>{line.reason}</Hint>}
      </View>
    </View>
  );
}

function PinPrompt({ visible, title, onSubmit, onCancel }: { visible: boolean; title: string; onSubmit: (pin: string) => void; onCancel: () => void }) {
  const t = useTheme();
  const [pin, setPin] = useState('');
  return (
    <Modal transparent animationType="fade" visible={visible} onRequestClose={onCancel}>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: t.bg }]}>
          <Text style={{ color: t.text, fontSize: 22, fontWeight: '800', marginBottom: 10 }}>{title}</Text>
          <TextInput value={pin} onChangeText={setPin} keyboardType="number-pad" secureTextEntry maxLength={8} autoFocus
            style={[styles.pin, { backgroundColor: t.fill, color: t.text }]} />
          <View style={{ flexDirection: 'row', gap: 10, marginTop: 12 }}>
            <Button kind="secondary" title="Cancel" onPress={() => { setPin(''); onCancel(); }} />
            <Button title="OK" onPress={() => { onSubmit(pin); setPin(''); }} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 4 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  brand: { fontSize: 20, fontWeight: '800', letterSpacing: -0.4 },
  conn: { marginLeft: 'auto', fontSize: 12 },
  banner: { borderLeftWidth: 4, borderRadius: 12, padding: 12, marginVertical: 8 },
  pills: { flexDirection: 'row', justifyContent: 'center', minHeight: 30 },
  pill: { fontSize: 13, fontWeight: '600', paddingVertical: 5, paddingHorizontal: 12, borderRadius: 999, overflow: 'hidden' },
  cardTitle: { fontSize: 15, fontWeight: '700', marginBottom: 8 },
  alert: { borderRadius: 18, padding: 14, marginBottom: 12 },
  section: { fontSize: 13, fontWeight: '600', letterSpacing: 0.8, marginTop: 18, marginBottom: 8, marginHorizontal: 6 },
  seg: { flexDirection: 'row', gap: 12, borderRadius: 14, padding: 10, paddingRight: 14, marginBottom: 6 },
  bar: { width: 4, borderRadius: 2 },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  score: { marginLeft: 'auto', fontSize: 12, fontWeight: '600', paddingHorizontal: 8, borderRadius: 999, overflow: 'hidden' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', alignItems: 'center', justifyContent: 'center', padding: 16 },
  sheet: { width: '100%', maxWidth: 360, borderRadius: 24, padding: 22, alignItems: 'center' },
  pin: { width: '100%', textAlign: 'center', fontSize: 28, letterSpacing: 8, borderRadius: 12, paddingVertical: 10 },
});
