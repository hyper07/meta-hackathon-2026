// Haptics, one word per meaning, so every screen feels the same. A device without haptics just stays quiet.
import * as Haptics from 'expo-haptics';

const safe = (p: () => Promise<void>) => { p().catch(() => {}); };

export const feel = {
  /** Any button or segment. */
  tap: () => safe(() => Haptics.selectionAsync()),
  /** A press that starts something: holding the orb to the end, starting to listen. */
  commit: () => safe(() => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)),
  /** Her voice was accepted ("Watch me", "I'm OK"). */
  verified: () => safe(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)),
  /** Another voice was refused. */
  refused: () => safe(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)),
  /** "Are you OK?" */
  attention: () => safe(() => Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning)),
};
