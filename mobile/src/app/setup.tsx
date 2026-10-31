// Setup: the server address, you, the people to alert, and your voice.
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, Field, Hint, SectionLabel, Segmented, SwitchRow } from '../components/ui';
import { int16ToBase64 } from '../lib/pcm';
import { api, ApiError } from '../lib/server';
import { useTheme } from '../lib/theme';
import { useWatchMe } from '../lib/watchme';

type Contact = { name: string; phone: string; email: string; relation: string; default: boolean; call: boolean };

const RELATIONS = ['mom', 'dad', 'sister', 'brother', 'partner', 'friend', 'roommate', 'other'];
const FAMILY = ['mom', 'dad', 'sister', 'brother'];
const LINES = [
  'Watch me. This is my voice, and only I can turn this on or off.',
  'I’m heading out tonight, so keep an eye on things for me.',
  'My name is on this phone, and this is how I normally talk.',
];

const blank = (): Contact => ({ name: '', phone: '', email: '', relation: '', default: false, call: true });

/** Server rule (messenger.recipients): the defaults she marked, else her family, else everyone listed. */
function route(contacts: Contact[]): string {
  const list = contacts.filter((c) => c.phone || c.email);
  if (!list.length) return 'No one to alert yet. Add a phone number or email.';
  const label = (c: Contact) => c.name || c.phone || c.email;
  const defaults = list.filter((c) => c.default), family = list.filter((c) => FAMILY.includes(c.relation));
  if (defaults.length) return `Alerts go to: ${defaults.map(label).join(', ')} · your default contacts`;
  if (family.length) return `Alerts go to: ${family.map(label).join(', ')} · no default set, so your family`;
  return `Alerts go to: ${list.map(label).join(', ')} · everyone listed`;
}

export default function Setup() {
  const t = useTheme();
  const w = useWatchMe();
  const p = w.profile;
  // The form starts from what the server has; when that changes (a new hello, a save), it starts over.
  const profileKey = JSON.stringify([p.name, p.sos_phrase, p.duress_phrase, p.contacts]);
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg }} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          <Text style={[styles.title, { color: t.text }]}>Setup</Text>
          <ServerCard key={w.serverUrl} />
          <ProfileForm key={profileKey} />
          <VoiceCard />
          <SectionLabel>Models and services</SectionLabel>
          <Card>
            {Object.entries(w.services).map(([k, v]) => (
              <View key={k} style={styles.service}>
                <Text style={{ color: t.muted }}>{k.replace(/_/g, ' ')}</Text>
                <Text style={{ color: t.text, flexShrink: 1, textAlign: 'right' }}>{String(v).replace(/^https?:\/\//, '')}</Text>
              </View>
            ))}
          </Card>
          <Hint style={{ textAlign: 'center' }}>On your phone today. Built for the Muse Charm pendant when Meta opens it to developers.</Hint>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function ServerCard() {
  const w = useWatchMe();
  const [url, setUrl] = useState(w.serverUrl);
  return (
    <>
      <SectionLabel>Server</SectionLabel>
      <Card>
        <Field label="Address" note="from ./run.sh --lan" value={url} onChangeText={setUrl} placeholder="192.168.1.20:8000"
          autoCapitalize="none" autoCorrect={false} keyboardType="url" />
        <View style={styles.row}><Button title="Connect" onPress={() => w.setServerUrl(url)} /></View>
        <Hint style={{ marginTop: 8 }}>{w.connected ? '● Connected' : w.serverUrl ? 'Not connected yet' : 'Not set'}</Hint>
      </Card>
    </>
  );
}

function ProfileForm() {
  const t = useTheme();
  const w = useWatchMe();
  const p = w.profile;
  const [name, setName] = useState<string>(p.name ?? '');
  const [pin, setPin] = useState('');
  const [sos, setSos] = useState<string>(p.sos_phrase ?? '');
  const [duress, setDuress] = useState<string>(p.duress_phrase ?? '');
  const [contacts, setContacts] = useState<Contact[]>(
    p.contacts?.length ? p.contacts.map((c: Partial<Contact>) => ({ ...blank(), ...c })) : [blank()]);
  const [message, setMessage] = useState('');

  const update = (i: number, patch: Partial<Contact>) => setContacts((cs) => cs.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  const save = async () => {
    setMessage('');
    try {
      const out = await api.post<Record<string, unknown>>(w.serverUrl, '/api/profile',
        { name, pin, sos_phrase: sos, duress_phrase: duress, contacts });
      w.setProfile({ type: 'profile', ...out });
      setPin('');
      setMessage('Saved.');
    } catch (e) { setMessage(e instanceof ApiError ? e.message : 'Couldn’t reach the server.'); }
  };

  return (
    <>
      <SectionLabel>You</SectionLabel>
      <Card>
        <Field label="Name" note="used in alerts" value={name} onChangeText={setName} />
        <Field label="PIN" note="4–8 digits; a fallback to stop, and to tap “I’m OK”" value={pin} onChangeText={setPin}
          keyboardType="number-pad" secureTextEntry placeholder={p.has_pin ? 'unchanged if blank' : ''} />
        <Field label="SOS phrase" note="alerts your people at once" value={sos} onChangeText={setSos} placeholder="e.g. purple elephant" />
        <Field label="Duress phrase" note="looks like it stops, keeps listening and alerts" value={duress} onChangeText={setDuress} />
      </Card>

      <SectionLabel>People to alert</SectionLabel>
      <Hint style={{ marginHorizontal: 6, marginBottom: 8 }}>Mark someone as Default and alerts go to them. With no default, alerts go to your family. Tell them first.</Hint>
      {contacts.map((c, i) => (
        <Card key={i}>
          <Field label="Name" value={c.name} onChangeText={(v) => update(i, { name: v })} />
          <Text style={[styles.small, { color: t.text }]}>Relationship</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Segmented options={RELATIONS.map((r) => ({ value: r, label: r[0].toUpperCase() + r.slice(1) }))}
              value={c.relation} onChange={(v) => update(i, { relation: v })} />
          </ScrollView>
          <Field label="Phone" note="+country code" value={c.phone} onChangeText={(v) => update(i, { phone: v })}
            keyboardType="phone-pad" placeholder="+12125551234" />
          <Field label="Email" value={c.email} onChangeText={(v) => update(i, { email: v })} keyboardType="email-address" autoCapitalize="none" />
          <SwitchRow label="Default · alerts go to this person" value={c.default} onValueChange={(v) => update(i, { default: v })} />
          <SwitchRow label="Also call this number" value={c.call} onValueChange={(v) => update(i, { call: v })} />
          <Button kind="link" title="Remove" onPress={() => setContacts((cs) => cs.filter((_, j) => j !== i))} />
        </Card>
      ))}
      <Button kind="link" title="+ Add a contact" onPress={() => setContacts((cs) => [...cs, blank()])} />
      <View style={[styles.route, { backgroundColor: t.tintBlue }]}><Text style={{ color: t.text }}>{route(contacts)}</Text></View>
      <Button big title="Save" onPress={save} />
      {!!message && <Hint style={{ textAlign: 'center', marginTop: 8 }}>{message}</Hint>}
    </>
  );
}

function VoiceCard() {
  const t = useTheme();
  const w = useWatchMe();
  const [step, setStep] = useState(0);
  const [samples, setSamples] = useState<string[]>([]);
  const [voiceMsg, setVoiceMsg] = useState('');

  const recordLine = async () => {
    setVoiceMsg(`Listening… read line ${step + 1} now.`);
    try {
      const pcm = await w.record(4);
      const next = [...samples, int16ToBase64(pcm)];
      if (next.length < 3) { setSamples(next); setStep(next.length); setVoiceMsg('Got it.'); return; }
      setVoiceMsg('Building your voiceprint…');
      const out = await api.post<Record<string, unknown> & { advice?: string }>(w.serverUrl, '/api/enroll', { samples: next });
      w.setProfile({ ...w.profile, ...out });
      setSamples([]); setStep(0);
      setVoiceMsg(out.advice ?? 'Saved. Only your voice can stop Watch Me now.');
    } catch (e) {
      setSamples([]); setStep(0);
      setVoiceMsg(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <>
      <SectionLabel>Your voice</SectionLabel>
      <Card>
        <Hint>Only your voice can start Watch Me, stop it, or answer “I’m OK”. Read each line once, in your normal voice.</Hint>
        {LINES.map((line, i) => (
          <View key={i} style={styles.step}>
            <View style={[styles.stepDot, { borderColor: i < step ? t.ok : i === step ? t.blue : t.fillStrong,
              backgroundColor: i < step ? t.ok : 'transparent' }]} />
            <Text style={{ color: i <= step ? t.text : t.muted, flex: 1, fontWeight: i === step ? '600' : '400' }}>“{line}”</Text>
          </View>
        ))}
        <View style={styles.row}><Button title={`Record line ${step + 1} of 3`} onPress={recordLine} disabled={!w.connected} /></View>
        {!!voiceMsg && <Hint style={{ marginTop: 8 }}>{voiceMsg}</Hint>}
        {w.profile.enrolled && (
          <View style={[styles.saved, { backgroundColor: t.tintOk }]}>
            <Text style={{ color: t.text, fontWeight: '700' }}>Voiceprint saved · {w.profile.voice_id}</Text>
            <Hint>70% match starts Watch Me. Stopping it, or answering “I’m OK”, needs 90%.</Hint>
          </View>
        )}
      </Card>
    </>
  );
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 60 },
  title: { fontSize: 30, fontWeight: '800', marginTop: 6 },
  row: { flexDirection: 'row', gap: 10, marginTop: 12 },
  small: { fontSize: 14, fontWeight: '600', marginTop: 12 },
  route: { borderRadius: 14, padding: 12, marginVertical: 12 },
  step: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', marginTop: 10 },
  stepDot: { width: 16, height: 16, borderRadius: 8, borderWidth: 2, marginTop: 2 },
  saved: { borderRadius: 14, padding: 12, marginTop: 12 },
  service: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, paddingVertical: 4 },
});
