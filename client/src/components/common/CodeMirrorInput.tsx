import { useMantineColorScheme, Input } from '@mantine/core';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { EditorState, Compartment, type Extension } from '@codemirror/state';
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter } from '@codemirror/view';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { yaml } from '@codemirror/lang-yaml';
import { oneDark } from '@codemirror/theme-one-dark';
import { foldGutter } from '@codemirror/language';
import { history, defaultKeymap, historyKeymap } from '@codemirror/commands';
import type { ContentType } from '../../types';

interface CodeMirrorInputProps {
  value?: string;
  onChange: (value: string) => void;
  language: ContentType;
  height?: string;
  readOnly?: boolean;
  placeholder?: string;
  label?: ReactNode;
  error?: ReactNode;
}

const languageMap: Record<ContentType, () => Extension> = {
  json: json,
  markdown: markdown,
  plaintext: () => [],
  yaml: yaml,
  html: markdown, // Fallback for HTML
};

export function CodeMirrorInput({
  value,
  onChange,
  language,
  height = '300px',
  readOnly = false,
  placeholder,
  label,
  error,
}: CodeMirrorInputProps): React.ReactElement {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const languageCompartment = useRef(new Compartment());
  const themeCompartment = useRef(new Compartment());
  const readOnlyCompartment = useRef(new Compartment());
  const [isInitialized, setIsInitialized] = useState(false);
  const { colorScheme } = useMantineColorScheme();

  const getLanguageExtension = (lang: ContentType): Extension => {
    const langFunc = languageMap[lang] || languageMap.plaintext;
    const extension = langFunc();
    return Array.isArray(extension) ? extension : [extension];
  };

  const getThemeExtension = (scheme: 'light' | 'dark' | 'auto'): Extension => {
    const effectiveScheme = scheme === 'auto' ? 'dark' : scheme;
    return effectiveScheme === 'dark' ? oneDark : [];
  };

  // Initialize Editor
  useEffect(() => {
    if (!editorRef.current) return;

    const updateListener = EditorView.updateListener.of((update: import('@codemirror/view').ViewUpdate) => {
      if (update.docChanged) {
        const newValue = update.state.doc.toString();
        onChange(newValue);
      }
    });

    const startState = EditorState.create({
      doc: value || '',
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        history(),
        foldGutter(),
        highlightActiveLine(),
        keymap.of([...defaultKeymap, ...historyKeymap]),
        languageCompartment.current.of(getLanguageExtension(language)),
        themeCompartment.current.of(getThemeExtension(colorScheme)),
        readOnlyCompartment.current.of(EditorState.readOnly.of(readOnly)),
        updateListener,
        EditorView.lineWrapping,
        EditorView.contentAttributes.of({
          placeholder: placeholder || '',
        }),
        EditorView.theme({
          '&': { height },
          '.cm-scroller': { overflow: 'auto' },
        }),
      ],
    });

    const view = new EditorView({
      state: startState,
      parent: editorRef.current,
    });

    viewRef.current = view;
    setIsInitialized(true);

    return () => {
      view.destroy();
    };
  }, [value, onChange, language, height, readOnly, placeholder, colorScheme]);

  // Update value externally
  useEffect(() => {
    if (viewRef.current && isInitialized && value !== viewRef.current.state.doc.toString()) {
      viewRef.current.dispatch({
        changes: { from: 0, to: viewRef.current.state.doc.length, insert: value },
      });
    }
  }, [value, isInitialized]);

  // Update language
  useEffect(() => {
    if (viewRef.current && isInitialized) {
      viewRef.current.dispatch({
        effects: languageCompartment.current.reconfigure(getLanguageExtension(language)),
      });
    }
  }, [language, isInitialized]);

  // Update theme
  useEffect(() => {
    if (viewRef.current && isInitialized) {
      viewRef.current.dispatch({
        effects: themeCompartment.current.reconfigure(getThemeExtension(colorScheme)),
      });
    }
  }, [colorScheme, isInitialized]);

  // Update readOnly
  useEffect(() => {
    if (viewRef.current && isInitialized) {
      viewRef.current.dispatch({
        effects: readOnlyCompartment.current.reconfigure(EditorState.readOnly.of(readOnly)),
      });
    }
  }, [readOnly, isInitialized]);

  return (
    <Input.Wrapper label={label} error={error}>
      <div
        ref={editorRef}
        style={{
          height,
          border: '1px solid var(--mantine-color-dark-4)',
          borderRadius: 'var(--mantine-radius-sm)',
          overflow: 'hidden',
        }}
      />
    </Input.Wrapper>
  );
}