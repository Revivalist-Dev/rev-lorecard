import { useMantineColorScheme, Paper } from '@mantine/core';
import { useEffect, useRef, useState } from 'react';
import { EditorState, Compartment, type Extension } from '@codemirror/state';
import { EditorView } from '@codemirror/view';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { yaml } from '@codemirror/lang-yaml';
import { createTheme } from '@uiw/codemirror-themes';
import { tags as t } from '@lezer/highlight';
import { foldGutter } from '@codemirror/language';
import { MergeView, type DirectMergeConfig } from '@codemirror/merge';
import { lineNumbers, highlightActiveLine, highlightActiveLineGutter, keymap } from '@codemirror/view';
import { history, defaultKeymap, historyKeymap } from '@codemirror/commands';
import type { ContentType } from '../../types';

const revDarkTheme = createTheme({
  theme: 'dark',
  settings: {
    background: '#2e2e2e',
    foreground: '#c9c9c9',
    caret: '#61afef',
    selection: '#444444',
    selectionMatch: '#444444',
    lineHighlight: '#353535',
    gutterBackground: '#242424',
    gutterForeground: '#c9c9c9',
  },
  styles: [
    // Placeholder styles to ensure theme is applied, actual syntax colors are handled by language extensions
    { tag: t.comment, color: '#8a3016' },
    { tag: t.variableName, color: '#61afef' },
    { tag: t.keyword, color: '#c678dd' },
    { tag: t.string, color: '#98c379' },
    { tag: t.number, color: '#d19a66' },
  ],
});

interface CodeMirrorDiffEditorProps {
  originalContent: string;
  modifiedContent: string;
  language: ContentType;
  height?: string;
  onModifiedChange?: (value: string) => void;
  onSelectionChange?: (selectedText: string) => void;
}

// Extend DirectMergeConfig to include sideBySide, which is missing in the current types
interface MergeConfigWithSideBySide extends DirectMergeConfig {
  sideBySide?: boolean;
}

const languageMap: Record<ContentType, () => Extension> = {
  json: json,
  markdown: markdown,
  plaintext: () => [], // Return empty array for plain text
  yaml: yaml,
  html: markdown, // Using markdown as a fallback for HTML
  // Character Card Formats
  cc_json_v1: json,
  cc_json_v2: json,
  cc_json_v3: json,
  cc_json_misc: json,
  cc_markdown_v1: markdown,
  cc_markdown_v2: markdown,
  cc_markdown_v3: markdown,
};

export function CodeMirrorDiffEditor({
  originalContent,
  modifiedContent,
  language,
  height = '650px',
  onModifiedChange,
  onSelectionChange,
}: CodeMirrorDiffEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const mergeViewRef = useRef<MergeView | null>(null);
  const languageCompartment = useRef(new Compartment());
  const themeCompartment = useRef(new Compartment());
  const [isInitialized, setIsInitialized] = useState(false);
  const { colorScheme } = useMantineColorScheme();

  const getLanguageExtension = (lang: ContentType): Extension => {
    const langFunc = languageMap[lang] || languageMap.plaintext;
    const extension = langFunc();
    // Ensure we return a single Extension or an array of Extensions
    return Array.isArray(extension) ? extension : [extension];
  };

  const getThemeExtension = (scheme: 'light' | 'dark' | 'auto'): Extension => {
    const effectiveScheme = scheme === 'auto' ? 'dark' : scheme;
    const isDark = effectiveScheme === 'dark';

    // Use the custom defined dark theme when dark mode is active
    return [isDark ? revDarkTheme : []];
  };

  // Initialize MergeView
  useEffect(() => {
    if (!editorRef.current) return;

    const updateListener = EditorView.updateListener.of((update: import('@codemirror/view').ViewUpdate) => {
      if (update.docChanged && typeof onModifiedChange === 'function') {
        const newValue = update.state.doc.toString();
        onModifiedChange(newValue);
      }
    });

    const selectionListener = EditorView.updateListener.of((update: import('@codemirror/view').ViewUpdate) => {
      if (update.selectionSet && typeof onSelectionChange === 'function') {
        const selection = update.state.selection.main;
        const selectedText = update.state.sliceDoc(selection.from, selection.to);
        onSelectionChange(selectedText);
      }
    });

    const extensions = [
      lineNumbers(),
      highlightActiveLineGutter(),
      history(),
      foldGutter(),
      highlightActiveLine(),
      keymap.of([...defaultKeymap, ...historyKeymap]),
      languageCompartment.current.of(getLanguageExtension(language)),
      themeCompartment.current.of(getThemeExtension(colorScheme)),
      EditorView.lineWrapping,
    ];

    const mergeView = new MergeView({
      a: {
        doc: originalContent,
        extensions: [
          ...extensions,
          EditorState.readOnly.of(true), // Original side is always read-only
        ],
      },
      b: {
        doc: modifiedContent,
        extensions: [
          ...extensions,
          // Force modified side to be editable, as per user requirement for this component's usage
          EditorState.readOnly.of(false),
          updateListener,
          selectionListener,
        ],
      },
      parent: editorRef.current,
      sideBySide: true, // Enable side-by-side view
      revertControls: undefined, // Removed 'none' which is invalid
    } as MergeConfigWithSideBySide); // Cast to the extended type to allow sideBySide

    mergeViewRef.current = mergeView;
    setIsInitialized(true);

    return () => {
      mergeView.destroy();
    };
  }, [language, height, onModifiedChange, onSelectionChange, colorScheme]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update original content
  useEffect(() => {
    if (mergeViewRef.current && isInitialized) {
      const aView = mergeViewRef.current.a;
      if (originalContent !== aView.state.doc.toString()) {
        aView.dispatch({
          changes: { from: 0, to: aView.state.doc.length, insert: originalContent },
        });
      }
    }
  }, [originalContent, isInitialized, mergeViewRef]);

  // Update modified content externally (e.g., when AI edit is applied)
  useEffect(() => {
    if (mergeViewRef.current && isInitialized && onModifiedChange === undefined) {
      const bView = mergeViewRef.current.b;
      if (modifiedContent !== bView.state.doc.toString()) {
        bView.dispatch({
          changes: { from: 0, to: bView.state.doc.length, insert: modifiedContent },
        });
      }
    }
  }, [modifiedContent, isInitialized, mergeViewRef, onModifiedChange]);

  // Update language
  useEffect(() => {
    if (mergeViewRef.current && isInitialized) {
      const langExtension = getLanguageExtension(language);
      const effects = languageCompartment.current.reconfigure(langExtension);
      mergeViewRef.current.a.dispatch({ effects });
      mergeViewRef.current.b.dispatch({ effects });
    }
  }, [language, isInitialized]);

  // Update theme
  useEffect(() => {
    if (mergeViewRef.current && isInitialized) {
      const themeExtension = getThemeExtension(colorScheme);
      const effects = themeCompartment.current.reconfigure(themeExtension);
      mergeViewRef.current.a.dispatch({ effects });
      mergeViewRef.current.b.dispatch({ effects });
    }
  }, [colorScheme, isInitialized]);

  return (
    <Paper withBorder p={0} style={{ overflowY: 'auto' }}>
      <div ref={editorRef} style={{ height }} />
    </Paper>
  );
}