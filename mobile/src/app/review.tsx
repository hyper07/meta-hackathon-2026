// Review: past sessions, colour-coded, and a session's timeline with its hash-chain check.
import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, Hint } from '../components/ui';
import { api } from '../lib/server';
import { levelColor, useTheme } from '../lib/theme';
import { useWatchMe, type Msg } from '../lib/watchme';

const worstLevel = (s: number) => (s >= 0.7 ? 'urgent' : s >= 0.45 ? 'concern' : s >= 0.2 ? 'watch' : 'none');

export default function Review() {
  const t = useTheme();
  const w = useWatchMe();
  const [list, setList] = useState<Msg[]>([]);
  const [open, setOpen] = useState<Msg | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!w.serverUrl) return;
    let live = true;
    api.get<Msg[]>(w.serverUrl, '/api/sessions').then((l) => { if (live) setList(l); }).catch(() => {});
    return () => { live = false; };
  }, [w.serverUrl, w.state]);

  const load = useCallback(async () => {
    if (!w.serverUrl) return;
    setLoading(true);
    try { setList(await api.get<Msg[]>(w.serverUrl, '/api/sessions')); } catch { /* keep the old list */ }
    finally { setLoading(false); }
  }, [w.serverUrl]);

  const show = async (id: string) => setOpen({ id, ...(await api.get<Msg>(w.serverUrl, `/api/sessions/${id}`)) });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: t.bg }} edges={['top']}>
      <ScrollView contentContainerStyle={styles.page} refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}>
        {!open ? (
          <>
            <Text style={[styles.title, { color: t.text }]}>Review</Text>
            {!list.length && <Hint>No sessions yet. Say “Watch me” to start one.</Hint>}
            {list.map((s) => (
              <Pressable key={s.id} onPress={() => show(s.id)}>
                <Card style={styles.rowCard}>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: t.text, fontWeight: '700' }}>{new Date(s.started * 1000).toLocaleString()}</Text>
                    <Hint>{s.segments} moments · {s.flagged} marked · {s.alerts} alerts</Hint>
                  </View>
                  <View style={[styles.dot, { backgroundColor: levelColor(t, worstLevel(s.worst)) }]} />
                </Card>
              </Pressable>
            ))}
          </>
        ) : (
          <>
            <Button kind="link" title="‹ Sessions" onPress={() => setOpen(null)} />
            <Text style={[styles.h, { color: t.text }]}>{new Date((open.events?.[0]?.t ?? 0) * 1000).toLocaleString()}</Text>
            <Text style={[styles.chain, { color: open.chain?.ok ? t.ok : t.red, backgroundColor: open.chain?.ok ? t.tintOk : t.tintRed }]}>
              {open.chain?.ok ? `✓ untouched · ${open.chain.lines} lines hash-chained` : `✗ altered at line ${open.chain?.broken_at}`}
            </Text>
            {[...(open.segments ?? []).map((x: Msg) => ({ ...x, _seg: true })), ...(open.events ?? [])]
              .sort((a, b) => a.t - b.t)
              .map((r: Msg, i: number) => r._seg ? (
                <View key={i} style={[styles.seg, { backgroundColor: t.surface }]}>
                  <View style={[styles.bar, { backgroundColor: levelColor(t, r.level) }]} />
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: 12, color: r.speaker === 'owner' ? t.blue : t.muted, fontWeight: '700' }}>
                      {r.speaker === 'owner' ? 'You' : 'Someone else'} · {new Date(r.t * 1000).toLocaleTimeString()}
                    </Text>
                    <Text style={{ color: t.text, marginTop: 2 }}>{r.text}</Text>
                    {!!r.reason && <Hint>{r.reason}</Hint>}
                  </View>
                </View>
              ) : (
                <Hint key={i} style={{ paddingVertical: 5, paddingHorizontal: 12 }}>◆ {r.kind.replace(/_/g, ' ')}{r.detail ? `: ${r.detail}` : ''}</Hint>
              ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 16, paddingBottom: 60 },
  title: { fontSize: 30, fontWeight: '800', marginTop: 6, marginBottom: 12 },
  h: { fontSize: 18, fontWeight: '800', marginTop: 4 },
  rowCard: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  dot: { width: 12, height: 12, borderRadius: 6 },
  chain: { alignSelf: 'flex-start', fontSize: 12, fontWeight: '600', paddingVertical: 3, paddingHorizontal: 10, borderRadius: 999, overflow: 'hidden', marginVertical: 10 },
  seg: { flexDirection: 'row', gap: 12, borderRadius: 14, padding: 10, marginBottom: 6 },
  bar: { width: 4, borderRadius: 2 },
});
