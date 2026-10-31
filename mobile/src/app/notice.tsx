// Notice: tell it what happened (typed, spoken or pasted), see which words match how the EEOC describes
// harassment, and the patterns per person. Nothing is sent to anyone.
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, Chip, Field, Hint, SectionLabel, Segmented } from '../components/ui';
import { int16ToBase64 } from '../lib/pcm';
import { api, ApiError } from '../lib/server';
import { useTheme } from '../lib/theme';
import { useWatchMe, type Msg } from '../lib/watchme';

type Setting = 'school' | 'work' | 'online' | 'other';
const HEAD: Record<string, string> = {
  none: 'Nothing here matches the usual descriptions of harassment.',
  some: 'Parts of this match what harassment policies describe.',
  clear: 'This matches what harassment policies describe.',
};

export default function Notice() {
  const t = useTheme();
  const w = useWatchMe();
  const [page, setPage] = useState<Msg | null>(null);
  const [text, setText] = useState('');
  const [setting, setSetting] = useState<Setting>('school');
  const [who, setWho] = useState('');
  const [where, setWhere] = useState('');
  const [picked, setPicked] = useState<Msg | null>(null);
  const [reloads, setReloads] = useState(0);
  const [busy, setBusy] = useState(false);
  const [saying, setSaying] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    if (!w.serverUrl) return;
    let live = true;
    api.get<Msg>(w.serverUrl, '/api/notice').then((p) => { if (live) setPage(p); }).catch(() => {});
    return () => { live = false; };
  }, [w.serverUrl, w.connected, w.lastReview, reloads]);
  const result = picked ?? w.lastReview;
  const setResult = setPicked;

  const check = async (audio?: string) => {
    setBusy(true); setMsg(audio ? 'Transcribing and checking…' : 'Checking…');
    try {
      const out = await api.post<Msg>(w.serverUrl, '/api/notice/debrief', { text, setting, who, where, audio });
      setPage(out); setResult(out.record); setText(''); setMsg('Saved to your record.'); setReloads((n) => n + 1);
    } catch (e) { setMsg(e instanceof ApiError ? e.message : 'Couldn’t reach the server.'); }
    finally { setBusy(false); }
  };

  const toggleSay = async () => {
    if (!saying) {
      try { await w.startCapture(); setSaying(true); setMsg('Listening. Say what happened, then tap Done. Only the words are kept.'); }
      catch (e) { setMsg(e instanceof Error ? e.message : String(e)); }
      return;
    }
    setSaying(false);
    const pcm = await w.stopCapture();
    await check(int16ToBase64(pcm));
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg }} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
          <Text style={[styles.title, { color: t.text }]}>Notice</Text>
          <Hint style={{ marginBottom: 12 }}>Something at school, work or online felt off? Tell it in your own words, or paste the messages. Only you see this.</Hint>
          <Card>
            <Field label="What happened" multiline value={text} onChangeText={setText}
              placeholder="What did they say or do, and what did you say? Their exact words help most." />
            <Segmented options={[{ value: 'school', label: 'School' }, { value: 'work', label: 'Work' }, { value: 'online', label: 'Online' }, { value: 'other', label: 'Other' }]}
              value={setting} onChange={(v) => setSetting(v as Setting)} />
            <View style={styles.row}>
              <View style={{ flex: 1 }}><Field label="Who" note="a name only you know" value={who} onChangeText={setWho} placeholder="e.g. Prof. R" /></View>
              <View style={{ flex: 1 }}><Field label="Where" value={where} onChangeText={setWhere} placeholder="e.g. office hours" /></View>
            </View>
            <View style={[styles.row, { marginTop: 14 }]}>
              <Button kind="secondary" title={saying ? '■ Done' : '🎙 Say it'} onPress={toggleSay} disabled={busy || !w.connected} />
              <Button kind="ai" title="Check it" onPress={() => check()} disabled={busy || saying || text.trim().length < 10} />
            </View>
            {!!msg && <Hint style={{ marginTop: 8 }}>{msg}</Hint>}
          </Card>

          {result && <Review record={result} page={page} />}

          {!!page?.patterns?.length && (
            <Card>
              <Text style={[styles.h, { color: t.text }]}>Patterns</Text>
              {page.patterns.map((p: Msg) => (
                <View key={p.who} style={{ marginTop: 10 }}>
                  <Text style={{ color: t.text }}><Text style={{ color: t.purple, fontSize: 24, fontWeight: '800' }}>{p.times}× </Text>
                    <Text style={{ fontWeight: '700' }}>{p.who}</Text> <Text style={{ color: t.muted }}>{p.first}{p.last !== p.first ? ` – ${p.last}` : ''}</Text></Text>
                  <View style={styles.chips}>{p.types.map((x: Msg) => <Chip key={x.type} color={t.purple} bg={t.tintPurple}>{x.label}{x.count > 1 ? ` ×${x.count}` : ''}</Chip>)}</View>
                </View>
              ))}
              {page.patterns.some((p: Msg) => p.repeated) && <Hint style={{ marginTop: 10 }}>{page.frequency}</Hint>}
            </Card>
          )}

          <SectionLabel>Your record</SectionLabel>
          {(page?.records ?? []).slice().reverse().map((r: Msg) => (
            <Card key={r.id}>
              <Text style={{ color: t.text, fontWeight: '700' }} onPress={() => setResult(r)}>{r.when.replace('T', ' ')}{r.who ? ` · ${r.who}` : ''}</Text>
              <Hint>{r.source === 'session' ? 'recorded session' : 'your account'}{r.pending ? ' · waiting for a connection' : ''}</Hint>
            </Card>
          ))}
          {!page?.records?.length && <Hint style={{ marginHorizontal: 6 }}>Nothing yet.</Hint>}
          {!!page && <Hint style={{ marginHorizontal: 6 }}>{page.chain?.ok ? `✓ ${page.records.length} entries, unaltered (hash-chained). Export from the web page.` : '✗ the record was altered'}</Hint>}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Review({ record, page }: { record: Msg; page: Msg | null }) {
  const t = useTheme();
  const r = record.review;
  if (!r) return <Card><Text style={[styles.h, { color: t.text }]}>Saved to your record.</Text>
    <Hint>{record.pending ? 'No connection right now. It will be checked automatically when you’re back online.' : 'The check isn’t available on this server.'}</Hint></Card>;
  if (r.error) return <Card><Text style={[styles.h, { color: t.text }]}>Saved to your record.</Text><Hint>The check didn’t finish. Try again later.</Hint></Card>;
  const types = page?.types ?? {};
  const resources = r.match === 'none' ? [] : [...(page?.resources?.[record.setting] ?? []), ...(page?.resources?.any ?? [])];
  return (
    <Card style={{ borderLeftWidth: 4, borderLeftColor: r.match === 'clear' ? t.purple : r.match === 'some' ? t.amber : t.fillStrong }}>
      <Hint>{record.when.replace('T', ' ')}{record.who ? ` · ${record.who}` : ''}</Hint>
      <Text style={[styles.h, { color: t.text }]}>{HEAD[r.match]}</Text>
      {!!r.summary && <Text style={{ color: t.text, marginTop: 6 }}>{r.summary}</Text>}
      {r.moments.map((m: Msg, i: number) => (
        <View key={i} style={[styles.moment, { borderTopColor: t.line }]}>
          <Chip color={t.purple} bg={t.tintPurple}>{types[m.type]?.label ?? m.type}</Chip>
          <Text style={[styles.quote, { backgroundColor: t.fill, color: t.text, borderLeftColor: t.purple }]}>“{m.quote}”</Text>
          <Hint>{m.why}</Hint>
          {types[m.type]?.plain && <Hint style={{ marginTop: 4 }}>{types[m.type].plain}</Hint>}
        </View>
      ))}
      {!!resources.length && (
        <View style={{ marginTop: 12 }}>
          <Text style={{ color: t.text, fontWeight: '700' }}>If you want to do something about it <Text style={{ color: t.muted, fontWeight: '400' }}>(only if you want to)</Text></Text>
          {resources.map((x: string, i: number) => <Hint key={i} style={{ marginTop: 4 }}>• {x}</Hint>)}
        </View>
      )}
      <Hint style={{ marginTop: 12 }}>{page?.disclaimer}</Hint>
    </Card>
  );
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 60 },
  title: { fontSize: 30, fontWeight: '800', marginTop: 6, marginBottom: 6 },
  row: { flexDirection: 'row', gap: 10 },
  h: { fontSize: 19, fontWeight: '800', marginTop: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 4 },
  moment: { borderTopWidth: StyleSheet.hairlineWidth, marginTop: 12, paddingTop: 10 },
  quote: { borderLeftWidth: 3, borderRadius: 10, padding: 10, marginVertical: 8, fontWeight: '600', overflow: 'hidden' },
});
