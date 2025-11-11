import { useMantineColorScheme } from '@mantine/core';
import { useEffect, useRef, useState } from 'react';
import { EditorState, Compartment, type Extension } from '@codemirror/state';
import { EditorView } from '@codemirror/view';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { yaml } from '@codemirror/lang-yaml';
import { oneDark } from '@codemirror/theme-one-dark';
import { foldGutter } from '@codemirror/language';
import { MergeView, type DirectMergeConfig } from '@codemirror/merge';
import { lineNumbers, highlightActiveLine, highlightActiveLineGutter, keymap } from '@codemirror/view';
import { history, defaultKeymap, historyKeymap } from '@codemirror/commands';
import type { ContentType } from '../../types';

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
};

export function CodeMirrorDiffEditor({
  originalContent,
  modifiedContent,
  language,
  height = '550px',
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

    const customTheme = EditorView.theme({
      // Set background color for the entire editor area
      '.cm-editor': {
        backgroundColor: isDark ? 'var(--mantine-color-dark-7) !important' : 'var(--mantine-color-white) !important',
        color: isDark ? 'var(--mantine-color-dark-0)' : 'var(--mantine-color-dark-7)',
      },
      // Ensure the content area also respects the background
      '.cm-content': {
        caretColor: isDark ? 'var(--mantine-color-white)' : 'var(--mantine-color-dark-7)',
      },
      // Style the gutters
      '.cm-gutters': {
        backgroundColor: isDark ? 'var(--mantine-color-dark-7)' : 'var(--mantine-color-gray-0)',
        color: isDark ? 'var(--mantine-color-dark-2)' : 'var(--mantine-color-gray-6)',
        borderRight: '1px solid var(--mantine-color-dark-4)',
      },
      // Style the line numbers
      '.cm-lineNumbers .cm-gutterElement': {
        color: isDark ? 'var(--mantine-color-dark-2)' : 'var(--mantine-color-gray-6)',
      },
    });

    return [isDark ? oneDark : [], customTheme];
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

  return <div ref={editorRef} style={{ height }} />;
}