import { useCallback, useEffect, useRef, useState } from "react";

// The Web Speech API isn't in TS's default DOM lib; treat the impls as unknown.
const SpeechRecognitionImpl: any =
  typeof window !== "undefined"
    ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : null;

/**
 * Browser-native speech: text-to-speech (read aloud) and speech-to-text
 * (dictation). No backend, no API keys. Degrades gracefully where unsupported
 * (STT needs Chrome/Edge).
 */
export function useSpeech(lang = "ru-RU") {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const supported = {
    tts: typeof window !== "undefined" && "speechSynthesis" in window,
    stt: !!SpeechRecognitionImpl,
  };

  const speak = useCallback(
    (text: string) => {
      if (!supported.tts || !text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      window.speechSynthesis.speak(utterance);
    },
    [lang, supported.tts],
  );

  const startListening = useCallback(
    (onText: (text: string) => void) => {
      if (!SpeechRecognitionImpl) return;
      const recognition = new SpeechRecognitionImpl();
      recognition.lang = lang;
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = (event: any) => {
        let finalText = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalText += event.results[i][0].transcript;
          }
        }
        if (finalText.trim()) onText(finalText.trim());
      };
      recognition.onend = () => setListening(false);
      recognition.onerror = () => setListening(false);
      recognitionRef.current = recognition;
      recognition.start();
      setListening(true);
    },
    [lang],
  );

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      if (typeof window !== "undefined") window.speechSynthesis?.cancel();
    };
  }, []);

  return { supported, listening, speak, startListening, stopListening };
}
