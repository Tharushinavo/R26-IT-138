// GENERATED FILE — do not hand-edit.
// Source: backend/contract/c-prompt-exemplars.json (label: "TEST_FIXTURE_ONLY").
// Regenerate with `npm run generate:c-prompt-exemplars` after the backend re-freezes the artefact.
//
// Data and types only. No node builtin, no `import.meta` -- this module is imported by
// application code and must survive Hermes bundling for iOS and Android.

export type ExemplarEntry = {
  blanks: number | null;
  difficulty_level: number;
  game_task_template_id: string;
  interactive_assets: Record<string, unknown>;
  prompt_payload: Record<string, unknown>;
  prompt_text: string;
  valid_action_space: Record<string, string>;
};

export const TEST_FIXTURE_ONLY_EXEMPLARS_LABEL = "TEST_FIXTURE_ONLY";

export const EXEMPLAR_ENTRIES: readonly ExemplarEntry[] = [
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-BT-01",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 3
    },
    "prompt_text": "How many tens and how many ones?",
    "valid_action_space": {
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-BT-01",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 7
    },
    "prompt_text": "How many tens and how many ones?",
    "valid_action_space": {
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-BT-01",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 29
    },
    "prompt_text": "How many tens and how many ones?",
    "valid_action_space": {
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-BT-01",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 69
    },
    "prompt_text": "How many tens and how many ones?",
    "valid_action_space": {
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-BT-01",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 37
    },
    "prompt_text": "How many tens and how many ones?",
    "valid_action_space": {
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-BT-02",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 185
    },
    "prompt_text": "How many hundreds, tens and ones?",
    "valid_action_space": {
      "hundreds": "int",
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-BT-02",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 100
    },
    "prompt_text": "How many hundreds, tens and ones?",
    "valid_action_space": {
      "hundreds": "int",
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-BT-02",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 98
    },
    "prompt_text": "How many hundreds, tens and ones?",
    "valid_action_space": {
      "hundreds": "int",
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-BT-02",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 434
    },
    "prompt_text": "How many hundreds, tens and ones?",
    "valid_action_space": {
      "hundreds": "int",
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-BT-02",
    "interactive_assets": {},
    "prompt_payload": {
      "target_number": 586
    },
    "prompt_text": "How many hundreds, tens and ones?",
    "valid_action_space": {
      "hundreds": "int",
      "ones": "int",
      "tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-BT-03",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 10,
      "pre_tens": 0
    },
    "prompt_text": "Change ten ones into one ten. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-BT-03",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 13,
      "pre_tens": 2
    },
    "prompt_text": "Change ten ones into one ten. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-BT-03",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 15,
      "pre_tens": 2
    },
    "prompt_text": "Change ten ones into one ten. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-BT-03",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 12,
      "pre_tens": 3
    },
    "prompt_text": "Change ten ones into one ten. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-BT-03",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 12,
      "pre_tens": 5
    },
    "prompt_text": "Change ten ones into one ten. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-BT-04",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 3,
      "pre_tens": 1
    },
    "prompt_text": "Change one ten into ten ones. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-BT-04",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 0,
      "pre_tens": 3
    },
    "prompt_text": "Change one ten into ten ones. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-BT-04",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 5,
      "pre_tens": 1
    },
    "prompt_text": "Change one ten into ten ones. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-BT-04",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 5,
      "pre_tens": 6
    },
    "prompt_text": "Change one ten into ten ones. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-BT-04",
    "interactive_assets": {},
    "prompt_payload": {
      "pre_ones": 4,
      "pre_tens": 3
    },
    "prompt_text": "Change one ten into ten ones. Now how many tens and ones?",
    "valid_action_space": {
      "post_ones": "int",
      "post_tens": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-CC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "distractor_object_ids": [],
      "valid_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2"
      ]
    },
    "prompt_text": "Tap each one time. Then write how many there are.",
    "valid_action_space": {
      "selected_object_ids": "list[str]",
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-CC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "distractor_object_ids": [
        "dist-0"
      ],
      "valid_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4"
      ]
    },
    "prompt_text": "Tap each one time. Then write how many there are.",
    "valid_action_space": {
      "selected_object_ids": "list[str]",
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-CC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "distractor_object_ids": [
        "dist-0",
        "dist-1"
      ],
      "valid_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7"
      ]
    },
    "prompt_text": "Tap each one time. Then write how many there are.",
    "valid_action_space": {
      "selected_object_ids": "list[str]",
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-CC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "distractor_object_ids": [
        "dist-0",
        "dist-1",
        "dist-2"
      ],
      "valid_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8",
        "obj-9",
        "obj-10",
        "obj-11"
      ]
    },
    "prompt_text": "Tap each one time. Then write how many there are.",
    "valid_action_space": {
      "selected_object_ids": "list[str]",
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-CC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "distractor_object_ids": [
        "dist-0",
        "dist-1",
        "dist-2",
        "dist-3"
      ],
      "valid_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8",
        "obj-9",
        "obj-10",
        "obj-11",
        "obj-12",
        "obj-13",
        "obj-14",
        "obj-15"
      ]
    },
    "prompt_text": "Tap each one time. Then write how many there are.",
    "valid_action_space": {
      "selected_object_ids": "list[str]",
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-CC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "available_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6"
      ],
      "target_n": 2
    },
    "prompt_text": "Tap to put this many in the box.",
    "valid_action_space": {
      "placed_object_ids": "list[str]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-CC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "available_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8"
      ],
      "target_n": 4
    },
    "prompt_text": "Tap to put this many in the box.",
    "valid_action_space": {
      "placed_object_ids": "list[str]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-CC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "available_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8",
        "obj-9",
        "obj-10",
        "obj-11"
      ],
      "target_n": 7
    },
    "prompt_text": "Tap to put this many in the box.",
    "valid_action_space": {
      "placed_object_ids": "list[str]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-CC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "available_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8",
        "obj-9",
        "obj-10",
        "obj-11",
        "obj-12",
        "obj-13",
        "obj-14",
        "obj-15"
      ],
      "target_n": 11
    },
    "prompt_text": "Tap to put this many in the box.",
    "valid_action_space": {
      "placed_object_ids": "list[str]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-CC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "available_object_ids": [
        "obj-0",
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
        "obj-5",
        "obj-6",
        "obj-7",
        "obj-8",
        "obj-9",
        "obj-10",
        "obj-11",
        "obj-12",
        "obj-13",
        "obj-14",
        "obj-15",
        "obj-16",
        "obj-17",
        "obj-18",
        "obj-19"
      ],
      "target_n": 15
    },
    "prompt_text": "Tap to put this many in the box.",
    "valid_action_space": {
      "placed_object_ids": "list[str]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-CC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        1,
        3
      ],
      "set_size": 3
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_numeral": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-CC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        5,
        6,
        8
      ],
      "set_size": 5
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_numeral": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-CC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        8,
        9,
        11
      ],
      "set_size": 8
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_numeral": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-CC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        12,
        13,
        14,
        15
      ],
      "set_size": 12
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_numeral": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-CC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        16,
        17,
        18,
        19
      ],
      "set_size": 16
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_numeral": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-CC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "object_count": 3,
      "trial_type": "rearrange_only"
    },
    "prompt_text": "Look at both pictures. Is the number the same or different?",
    "valid_action_space": {
      "judgment": "same|changed"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-CC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "object_count": 4,
      "trial_type": "add_remove"
    },
    "prompt_text": "Look at both pictures. Is the number the same or different?",
    "valid_action_space": {
      "judgment": "same|changed"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-CC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "object_count": 6,
      "trial_type": "rearrange_only"
    },
    "prompt_text": "Look at both pictures. Is the number the same or different?",
    "valid_action_space": {
      "judgment": "same|changed"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-CC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "object_count": 8,
      "trial_type": "rearrange_only"
    },
    "prompt_text": "Look at both pictures. Is the number the same or different?",
    "valid_action_space": {
      "judgment": "same|changed"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-CC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "object_count": 10,
      "trial_type": "add_remove"
    },
    "prompt_text": "Look at both pictures. Is the number the same or different?",
    "valid_action_space": {
      "judgment": "same|changed"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-EG-01",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 2,
      "number_of_groups": 2
    },
    "prompt_text": "Make the groups. Put the same number in each group.",
    "valid_action_space": {
      "groups": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-EG-01",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 2,
      "number_of_groups": 3
    },
    "prompt_text": "Make the groups. Put the same number in each group.",
    "valid_action_space": {
      "groups": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-EG-01",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 3,
      "number_of_groups": 3
    },
    "prompt_text": "Make the groups. Put the same number in each group.",
    "valid_action_space": {
      "groups": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-EG-01",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 3,
      "number_of_groups": 4
    },
    "prompt_text": "Make the groups. Put the same number in each group.",
    "valid_action_space": {
      "groups": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-EG-01",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 4,
      "number_of_groups": 5
    },
    "prompt_text": "Make the groups. Put the same number in each group.",
    "valid_action_space": {
      "groups": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-EG-02",
    "interactive_assets": {},
    "prompt_payload": {
      "cols": 2,
      "direction": "read",
      "rows": 2
    },
    "prompt_text": "Write a number in each box.",
    "valid_action_space": {
      "cols": "int",
      "rows": "int",
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-EG-02",
    "interactive_assets": {},
    "prompt_payload": {
      "cols": 2,
      "direction": "read",
      "rows": 3
    },
    "prompt_text": "Write a number in each box.",
    "valid_action_space": {
      "cols": "int",
      "rows": "int",
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-EG-02",
    "interactive_assets": {},
    "prompt_payload": {
      "cols": 3,
      "direction": "read",
      "rows": 3
    },
    "prompt_text": "Write a number in each box.",
    "valid_action_space": {
      "cols": "int",
      "rows": "int",
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-EG-02",
    "interactive_assets": {},
    "prompt_payload": {
      "cols": 4,
      "direction": "read",
      "rows": 4
    },
    "prompt_text": "Write a number in each box.",
    "valid_action_space": {
      "cols": "int",
      "rows": "int",
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-EG-02",
    "interactive_assets": {},
    "prompt_payload": {
      "cols": 5,
      "direction": "build",
      "rows": 5
    },
    "prompt_text": "Make the rows of squares shown.",
    "valid_action_space": {
      "cols": "int",
      "rows": "int",
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-EG-03",
    "interactive_assets": {},
    "prompt_payload": {
      "multiplicand": 4,
      "multiplier": 5
    },
    "prompt_text": "How many are there in all the groups?",
    "valid_action_space": {
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-EG-03",
    "interactive_assets": {},
    "prompt_payload": {
      "multiplicand": 5,
      "multiplier": 2
    },
    "prompt_text": "How many are there in all the groups?",
    "valid_action_space": {
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-EG-03",
    "interactive_assets": {},
    "prompt_payload": {
      "multiplicand": 1,
      "multiplier": 2
    },
    "prompt_text": "How many are there in all the groups?",
    "valid_action_space": {
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-EG-03",
    "interactive_assets": {},
    "prompt_payload": {
      "multiplicand": 3,
      "multiplier": 5
    },
    "prompt_text": "How many are there in all the groups?",
    "valid_action_space": {
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-EG-03",
    "interactive_assets": {},
    "prompt_payload": {
      "multiplicand": 6,
      "multiplier": 5
    },
    "prompt_text": "How many are there in all the groups?",
    "valid_action_space": {
      "submitted_product": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-JB-01",
    "interactive_assets": {},
    "prompt_payload": {
      "count_a": 3,
      "count_b": 2
    },
    "prompt_text": "How many are there in both groups?",
    "valid_action_space": {
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-JB-01",
    "interactive_assets": {},
    "prompt_payload": {
      "count_a": 4,
      "count_b": 5
    },
    "prompt_text": "How many are there in both groups?",
    "valid_action_space": {
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-JB-01",
    "interactive_assets": {},
    "prompt_payload": {
      "count_a": 1,
      "count_b": 6
    },
    "prompt_text": "How many are there in both groups?",
    "valid_action_space": {
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-JB-01",
    "interactive_assets": {},
    "prompt_payload": {
      "count_a": 9,
      "count_b": 8
    },
    "prompt_text": "How many are there in both groups?",
    "valid_action_space": {
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-JB-01",
    "interactive_assets": {},
    "prompt_payload": {
      "count_a": 9,
      "count_b": 14
    },
    "prompt_text": "How many are there in both groups?",
    "valid_action_space": {
      "submitted_total": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-JB-02",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 2,
      "addend_b": 2,
      "start": 2
    },
    "prompt_text": "Use the jump buttons to add. What number do you stop at?",
    "valid_action_space": {
      "final_position": "int",
      "jumps": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-JB-02",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 2,
      "addend_b": 5,
      "start": 5
    },
    "prompt_text": "Use the jump buttons to add. What number do you stop at?",
    "valid_action_space": {
      "final_position": "int",
      "jumps": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-JB-02",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 7,
      "addend_b": 1,
      "start": 7
    },
    "prompt_text": "Use the jump buttons to add. What number do you stop at?",
    "valid_action_space": {
      "final_position": "int",
      "jumps": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-JB-02",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 1,
      "addend_b": 10,
      "start": 10
    },
    "prompt_text": "Use the jump buttons to add. What number do you stop at?",
    "valid_action_space": {
      "final_position": "int",
      "jumps": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-JB-02",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 3,
      "addend_b": 9,
      "start": 9
    },
    "prompt_text": "Use the jump buttons to add. What number do you stop at?",
    "valid_action_space": {
      "final_position": "int",
      "jumps": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-JB-03",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 4,
      "addend_b": 3
    },
    "prompt_text": "Add the two numbers.",
    "valid_action_space": {
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-JB-03",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 6,
      "addend_b": 4
    },
    "prompt_text": "Add the two numbers.",
    "valid_action_space": {
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-JB-03",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 7,
      "addend_b": 2
    },
    "prompt_text": "Add the two numbers.",
    "valid_action_space": {
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-JB-03",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 1,
      "addend_b": 0
    },
    "prompt_text": "Add the two numbers.",
    "valid_action_space": {
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-JB-03",
    "interactive_assets": {},
    "prompt_payload": {
      "addend_a": 3,
      "addend_b": 9
    },
    "prompt_text": "Add the two numbers.",
    "valid_action_space": {
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-JB-04",
    "interactive_assets": {},
    "prompt_payload": {
      "operand_a": 13,
      "operand_b": 10
    },
    "prompt_text": "Add the two numbers. Did you change ten ones into a ten?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-JB-04",
    "interactive_assets": {},
    "prompt_payload": {
      "operand_a": 13,
      "operand_b": 18
    },
    "prompt_text": "Add the two numbers. Did you change ten ones into a ten?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-JB-04",
    "interactive_assets": {},
    "prompt_payload": {
      "operand_a": 26,
      "operand_b": 27
    },
    "prompt_text": "Add the two numbers. Did you change ten ones into a ten?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-JB-04",
    "interactive_assets": {},
    "prompt_payload": {
      "operand_a": 23,
      "operand_b": 43
    },
    "prompt_text": "Add the two numbers. Did you change ten ones into a ten?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-JB-04",
    "interactive_assets": {},
    "prompt_payload": {
      "operand_a": 38,
      "operand_b": 96
    },
    "prompt_text": "Add the two numbers. Did you change ten ones into a ten?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_sum": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-MCL-01",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        3,
        5,
        9
      ],
      "target_representation_value": 9
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_value": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-MCL-01",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        6,
        13,
        20
      ],
      "target_representation_value": 13
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_value": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-MCL-01",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        0,
        2,
        7,
        14
      ],
      "target_representation_value": 2
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_value": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-MCL-01",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        16,
        32,
        34,
        41
      ],
      "target_representation_value": 32
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_value": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-MCL-01",
    "interactive_assets": {},
    "prompt_payload": {
      "numeral_options": [
        21,
        35,
        46,
        47,
        66
      ],
      "target_representation_value": 66
    },
    "prompt_text": "How many are there? Tap the number.",
    "valid_action_space": {
      "selected_value": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-MCL-02",
    "interactive_assets": {},
    "prompt_payload": {
      "left_count": 1,
      "right_count": 10
    },
    "prompt_text": "Which side has more? Or are they the same?",
    "valid_action_space": {
      "selection": "left|right|equal"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-MCL-02",
    "interactive_assets": {},
    "prompt_payload": {
      "left_count": 6,
      "right_count": 8
    },
    "prompt_text": "Which side has more? Or are they the same?",
    "valid_action_space": {
      "selection": "left|right|equal"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-MCL-02",
    "interactive_assets": {},
    "prompt_payload": {
      "left_count": 10,
      "right_count": 27
    },
    "prompt_text": "Which side has more? Or are they the same?",
    "valid_action_space": {
      "selection": "left|right|equal"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-MCL-02",
    "interactive_assets": {},
    "prompt_payload": {
      "left_count": 9,
      "right_count": 23
    },
    "prompt_text": "Which side has more? Or are they the same?",
    "valid_action_space": {
      "selection": "left|right|equal"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-MCL-02",
    "interactive_assets": {},
    "prompt_payload": {
      "left_count": 77,
      "right_count": 66
    },
    "prompt_text": "Which side has more? Or are they the same?",
    "valid_action_space": {
      "selection": "left|right|equal"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-MCL-03",
    "interactive_assets": {},
    "prompt_payload": {
      "value_a": 8,
      "value_b": 8
    },
    "prompt_text": "Less than, more than, or the same?",
    "valid_action_space": {
      "comparison_sign": "<|>|="
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-MCL-03",
    "interactive_assets": {},
    "prompt_payload": {
      "value_a": 3,
      "value_b": 4
    },
    "prompt_text": "Less than, more than, or the same?",
    "valid_action_space": {
      "comparison_sign": "<|>|="
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-MCL-03",
    "interactive_assets": {},
    "prompt_payload": {
      "value_a": 70,
      "value_b": 23
    },
    "prompt_text": "Less than, more than, or the same?",
    "valid_action_space": {
      "comparison_sign": "<|>|="
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-MCL-03",
    "interactive_assets": {},
    "prompt_payload": {
      "value_a": 15,
      "value_b": 170
    },
    "prompt_text": "Less than, more than, or the same?",
    "valid_action_space": {
      "comparison_sign": "<|>|="
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-MCL-03",
    "interactive_assets": {},
    "prompt_payload": {
      "value_a": 585,
      "value_b": 145
    },
    "prompt_text": "Less than, more than, or the same?",
    "valid_action_space": {
      "comparison_sign": "<|>|="
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-MCL-04",
    "interactive_assets": {},
    "prompt_payload": {
      "interval_max": 10,
      "target_position": 2
    },
    "prompt_text": "Tap the buttons to go to the number.",
    "valid_action_space": {
      "marker_position": "number"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-MCL-04",
    "interactive_assets": {},
    "prompt_payload": {
      "interval_max": 20,
      "target_position": 7
    },
    "prompt_text": "Tap the buttons to go to the number.",
    "valid_action_space": {
      "marker_position": "number"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-MCL-04",
    "interactive_assets": {},
    "prompt_payload": {
      "interval_max": 50,
      "target_position": 26
    },
    "prompt_text": "Tap the buttons to go to the number.",
    "valid_action_space": {
      "marker_position": "number"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-MCL-04",
    "interactive_assets": {},
    "prompt_payload": {
      "interval_max": 100,
      "target_position": 36
    },
    "prompt_text": "Tap the buttons to go to the number.",
    "valid_action_space": {
      "marker_position": "number"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-MCL-04",
    "interactive_assets": {},
    "prompt_payload": {
      "interval_max": 200,
      "target_position": 34
    },
    "prompt_text": "Tap the buttons to go to the number.",
    "valid_action_space": {
      "marker_position": "number"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 1,
    "game_task_template_id": "C-NP-01",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        6,
        7,
        8
      ]
    },
    "prompt_text": "What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 2,
    "game_task_template_id": "C-NP-01",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        14,
        15,
        16
      ]
    },
    "prompt_text": "What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 3,
    "game_task_template_id": "C-NP-01",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        38,
        39,
        40,
        41
      ]
    },
    "prompt_text": "What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 4,
    "game_task_template_id": "C-NP-01",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        60,
        61,
        62,
        63
      ]
    },
    "prompt_text": "What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 5,
    "game_task_template_id": "C-NP-01",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        9,
        10,
        11,
        12,
        13
      ]
    },
    "prompt_text": "What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 1,
    "game_task_template_id": "C-NP-02",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        5,
        4,
        3
      ]
    },
    "prompt_text": "What number comes just before this one?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 2,
    "game_task_template_id": "C-NP-02",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        18,
        17,
        16
      ]
    },
    "prompt_text": "What number comes just before this one?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 3,
    "game_task_template_id": "C-NP-02",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        24,
        23,
        22,
        21
      ]
    },
    "prompt_text": "What number comes just before this one?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 4,
    "game_task_template_id": "C-NP-02",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        26,
        25,
        24,
        23
      ]
    },
    "prompt_text": "What number comes just before this one?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 5,
    "game_task_template_id": "C-NP-02",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        74,
        73,
        72,
        71,
        70
      ]
    },
    "prompt_text": "What number comes just before this one?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 1,
    "game_task_template_id": "C-NP-03",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        3,
        8,
        13
      ],
      "step": 5
    },
    "prompt_text": "Keep counting the same way. What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 1,
    "difficulty_level": 2,
    "game_task_template_id": "C-NP-03",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        19,
        24,
        29
      ],
      "step": 5
    },
    "prompt_text": "Keep counting the same way. What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 3,
    "game_task_template_id": "C-NP-03",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        18,
        20,
        22,
        24
      ],
      "step": 2
    },
    "prompt_text": "Keep counting the same way. What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 4,
    "game_task_template_id": "C-NP-03",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        14,
        24,
        34,
        44
      ],
      "step": 10
    },
    "prompt_text": "Keep counting the same way. What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": 2,
    "difficulty_level": 5,
    "game_task_template_id": "C-NP-03",
    "interactive_assets": {},
    "prompt_payload": {
      "shown_sequence": [
        0,
        2,
        4,
        6,
        8
      ],
      "step": 2
    },
    "prompt_text": "Keep counting the same way. What number comes next?",
    "valid_action_space": {
      "entered_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-NP-04",
    "interactive_assets": {},
    "prompt_payload": {
      "direction": "ascending",
      "values": [
        3,
        0,
        2
      ]
    },
    "prompt_text": "Put these in order. Small to big.",
    "valid_action_space": {
      "arranged_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-NP-04",
    "interactive_assets": {},
    "prompt_payload": {
      "direction": "ascending",
      "values": [
        9,
        28,
        7
      ]
    },
    "prompt_text": "Put these in order. Small to big.",
    "valid_action_space": {
      "arranged_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-NP-04",
    "interactive_assets": {},
    "prompt_payload": {
      "direction": "descending",
      "values": [
        7,
        58,
        29,
        52
      ]
    },
    "prompt_text": "Put these in order. Big to small.",
    "valid_action_space": {
      "arranged_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-NP-04",
    "interactive_assets": {},
    "prompt_payload": {
      "direction": "ascending",
      "values": [
        70,
        87,
        8,
        49
      ]
    },
    "prompt_text": "Put these in order. Small to big.",
    "valid_action_space": {
      "arranged_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-NP-04",
    "interactive_assets": {},
    "prompt_payload": {
      "direction": "ascending",
      "values": [
        114,
        43,
        101,
        121,
        45
      ]
    },
    "prompt_text": "Put these in order. Small to big.",
    "valid_action_space": {
      "arranged_values": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-SF-01",
    "interactive_assets": {},
    "prompt_payload": {
      "recipient_count": 2,
      "total": 2
    },
    "prompt_text": "Share them equally. How many does each get?",
    "valid_action_space": {
      "allocations": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-SF-01",
    "interactive_assets": {},
    "prompt_payload": {
      "recipient_count": 2,
      "total": 6
    },
    "prompt_text": "Share them equally. How many does each get?",
    "valid_action_space": {
      "allocations": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-SF-01",
    "interactive_assets": {},
    "prompt_payload": {
      "recipient_count": 3,
      "total": 3
    },
    "prompt_text": "Share them equally. How many does each get?",
    "valid_action_space": {
      "allocations": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-SF-01",
    "interactive_assets": {},
    "prompt_payload": {
      "recipient_count": 4,
      "total": 4
    },
    "prompt_text": "Share them equally. How many does each get?",
    "valid_action_space": {
      "allocations": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-SF-01",
    "interactive_assets": {},
    "prompt_payload": {
      "recipient_count": 5,
      "total": 5
    },
    "prompt_text": "Share them equally. How many does each get?",
    "valid_action_space": {
      "allocations": "list[int]"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-SF-02",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 2,
      "total": 4
    },
    "prompt_text": "Make equal groups of this size. Show the groups you made.",
    "valid_action_space": {
      "groups": "list[int]",
      "submitted_group_count": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-SF-02",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 2,
      "total": 6
    },
    "prompt_text": "Make equal groups of this size. Show the groups you made.",
    "valid_action_space": {
      "groups": "list[int]",
      "submitted_group_count": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-SF-02",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 3,
      "total": 9
    },
    "prompt_text": "Make equal groups of this size. Show the groups you made.",
    "valid_action_space": {
      "groups": "list[int]",
      "submitted_group_count": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-SF-02",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 3,
      "total": 12
    },
    "prompt_text": "Make equal groups of this size. Show the groups you made.",
    "valid_action_space": {
      "groups": "list[int]",
      "submitted_group_count": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-SF-02",
    "interactive_assets": {},
    "prompt_payload": {
      "group_size": 4,
      "total": 20
    },
    "prompt_text": "Make equal groups of this size. Show the groups you made.",
    "valid_action_space": {
      "groups": "list[int]",
      "submitted_group_count": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-SF-03",
    "interactive_assets": {},
    "prompt_payload": {
      "dividend": 4
    },
    "prompt_text": "What is half of this number?",
    "valid_action_space": {
      "submitted_quotient": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-SF-03",
    "interactive_assets": {},
    "prompt_payload": {
      "dividend": 8
    },
    "prompt_text": "What is half of this number?",
    "valid_action_space": {
      "submitted_quotient": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-SF-03",
    "interactive_assets": {},
    "prompt_payload": {
      "dividend": 0
    },
    "prompt_text": "What is half of this number?",
    "valid_action_space": {
      "submitted_quotient": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-SF-03",
    "interactive_assets": {},
    "prompt_payload": {
      "dividend": 2
    },
    "prompt_text": "What is half of this number?",
    "valid_action_space": {
      "submitted_quotient": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-SF-03",
    "interactive_assets": {},
    "prompt_payload": {
      "dividend": 30
    },
    "prompt_text": "What is half of this number?",
    "valid_action_space": {
      "submitted_quotient": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-TC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "initial_count": 1,
      "removed_count": 1
    },
    "prompt_text": "Take away this many. How many are left?",
    "valid_action_space": {
      "submitted_remainder": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-TC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "initial_count": 1,
      "removed_count": 0
    },
    "prompt_text": "Take away this many. How many are left?",
    "valid_action_space": {
      "submitted_remainder": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-TC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "initial_count": 6,
      "removed_count": 5
    },
    "prompt_text": "Take away this many. How many are left?",
    "valid_action_space": {
      "submitted_remainder": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-TC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "initial_count": 15,
      "removed_count": 15
    },
    "prompt_text": "Take away this many. How many are left?",
    "valid_action_space": {
      "submitted_remainder": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-TC-01",
    "interactive_assets": {},
    "prompt_payload": {
      "initial_count": 4,
      "removed_count": 2
    },
    "prompt_text": "Take away this many. How many are left?",
    "valid_action_space": {
      "submitted_remainder": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-TC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "directed": false,
      "value_a": 1,
      "value_b": 2
    },
    "prompt_text": "How many more? Or how many fewer?",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-TC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "directed": false,
      "value_a": 5,
      "value_b": 6
    },
    "prompt_text": "How many more? Or how many fewer?",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-TC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "directed": false,
      "value_a": 6,
      "value_b": 8
    },
    "prompt_text": "How many more? Or how many fewer?",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-TC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "directed": false,
      "value_a": 8,
      "value_b": 15
    },
    "prompt_text": "How many more? Or how many fewer?",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-TC-02",
    "interactive_assets": {},
    "prompt_payload": {
      "directed": true,
      "value_a": 5,
      "value_b": 9
    },
    "prompt_text": "How many more? Or how many fewer?",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-TC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 3,
      "subtrahend": 1
    },
    "prompt_text": "Take the second number away from the first.",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-TC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 1,
      "subtrahend": 1
    },
    "prompt_text": "Take the second number away from the first.",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-TC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 5,
      "subtrahend": 4
    },
    "prompt_text": "Take the second number away from the first.",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-TC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 8,
      "subtrahend": 6
    },
    "prompt_text": "Take the second number away from the first.",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-TC-03",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 5,
      "subtrahend": 0
    },
    "prompt_text": "Take the second number away from the first.",
    "valid_action_space": {
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 1,
    "game_task_template_id": "C-TC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 20,
      "subtrahend": 7
    },
    "prompt_text": "Take the second number away from the first. Did you change a ten into ones?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 2,
    "game_task_template_id": "C-TC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 20,
      "subtrahend": 15
    },
    "prompt_text": "Take the second number away from the first. Did you change a ten into ones?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 3,
    "game_task_template_id": "C-TC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 38,
      "subtrahend": 17
    },
    "prompt_text": "Take the second number away from the first. Did you change a ten into ones?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 4,
    "game_task_template_id": "C-TC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 26,
      "subtrahend": 11
    },
    "prompt_text": "Take the second number away from the first. Did you change a ten into ones?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_difference": "int"
    }
  },
  {
    "blanks": null,
    "difficulty_level": 5,
    "game_task_template_id": "C-TC-04",
    "interactive_assets": {},
    "prompt_payload": {
      "minuend": 66,
      "subtrahend": 10
    },
    "prompt_text": "Take the second number away from the first. Did you change a ten into ones?",
    "valid_action_space": {
      "exchange_performed": "bool",
      "submitted_difference": "int"
    }
  }
];
