window.SEQUENCE_EVIDENCE = [
  {
    "step": 0,
    "nodes": 4,
    "edges": 3,
    "font": 16,
    "canvas": [
      1200,
      900
    ],
    "file": "00-original.svg",
    "sha256": "cb0cf517aa2ab4c7e1233c03400b4df563d2efc5e46849874a3dd93a844530cb",
    "accepted": true
  },
  {
    "step": 1,
    "nodes": 4,
    "edges": 3,
    "font": 16,
    "canvas": [
      1200,
      900
    ],
    "file": "01-edited.svg",
    "sha256": "7a06d856113937abcab294e11377d7d397ce0abfea5c66740c91f8c72607f429",
    "accepted": true,
    "request": {
      "name": "longer label",
      "labels": {
        "n1": "Representation consistency verification"
      },
      "flow": "free"
    },
    "seconds": 0.009225666988641024,
    "certificate": null
  },
  {
    "step": 2,
    "nodes": 4,
    "edges": 3,
    "font": 24,
    "canvas": [
      1200,
      900
    ],
    "file": "02-edited.svg",
    "sha256": "02f17516d72aa8d795997b73748a4f6dc7cd5f5d9b7b2965d3fd23c30d0b0174",
    "accepted": true,
    "request": {
      "name": "larger font",
      "font_size": 24,
      "flow": "free"
    },
    "seconds": 0.0072988339816220105,
    "certificate": null
  },
  {
    "step": 3,
    "nodes": 4,
    "edges": 3,
    "font": 24,
    "canvas": [
      320,
      1700
    ],
    "file": "03-edited.svg",
    "sha256": "010932cd918dda08b133d6fd0276d31f25aba39b7a31533111327f11753c03ca",
    "accepted": true,
    "request": {
      "name": "portrait layout",
      "width": 320,
      "height": 1700,
      "flow": "vertical"
    },
    "seconds": 0.004190416948404163,
    "certificate": null
  },
  {
    "step": 4,
    "nodes": 5,
    "edges": 4,
    "font": 24,
    "canvas": [
      320,
      2000
    ],
    "file": "04-edited.svg",
    "sha256": "d8638ab182cd325fa6b72f896b35fc962ddc68b29ef973845fb5faa4538626a6",
    "accepted": true,
    "request": {
      "name": "explicit branch",
      "branch": [
        "n1",
        "review",
        "Independent check"
      ],
      "height": 2000,
      "flow": "vertical"
    },
    "seconds": 0.00857100001303479,
    "certificate": null
  },
  {
    "step": 5,
    "nodes": 5,
    "edges": 4,
    "font": 24,
    "canvas": [
      2000,
      900
    ],
    "file": "05-edited.svg",
    "sha256": "b6d8f98c257b160ac0c62e8f85bdcd35e4c7635f5d7417f7afc5497582f03f65",
    "accepted": true,
    "request": {
      "name": "landscape layout",
      "width": 2000,
      "height": 900,
      "flow": "horizontal"
    },
    "seconds": 0.00637787498999387,
    "certificate": null
  },
  {
    "step": 6,
    "nodes": 5,
    "edges": 4,
    "font": 18,
    "canvas": [
      1400,
      700
    ],
    "file": "06-edited.svg",
    "sha256": "b012c86797c21831c5c37896141f00678850cada380036bc3c43c05696222660",
    "accepted": true,
    "request": {
      "name": "short label and smaller font",
      "labels": {
        "n1": "Checked"
      },
      "font_size": 18,
      "width": 1400,
      "height": 700,
      "flow": "horizontal"
    },
    "seconds": 0.005222833016887307,
    "certificate": null
  },
  {
    "step": 7,
    "nodes": 5,
    "edges": 4,
    "font": 18,
    "canvas": [
      80,
      60
    ],
    "file": "06-edited.svg",
    "sha256": null,
    "accepted": false,
    "request": {
      "name": "impossible canvas",
      "width": 80,
      "height": 60,
      "flow": "horizontal",
      "expected_rejection": true
    },
    "seconds": 0.0012373750214464962,
    "certificate": {
      "schema_version": 1,
      "subject_sha256": "2347977429422d25013ed2104e64a04eee9bc5ac7c001d5b977cfdde7c027d2d",
      "flow": "horizontal",
      "gap": 24,
      "padding": 16,
      "scope": "Necessary-condition witness for fitted rectangular geometry; not an author-intent judgment or a minimum repair",
      "kind": "node_canvas",
      "node_id": "n0",
      "axis": "width",
      "required": 150.0,
      "available": 48,
      "shortfall": 102.0
    }
  }
];
