from json import loads

import pytest

from robotoff.insights.question import CategoryQuestionFormatter, get_display_image


@pytest.mark.parametrize(
    "source_image,output",
    [
        ("/366/194/903/0038/1.jpg", "/366/194/903/0038/1.400.jpg"),
        ("/366/194/903/0038/20.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20.400.jpg", "/366/194/903/0038/20.400.jpg"),
        ("/366/194/903/0038/20test.jpg", "/366/194/903/0038/20test.jpg"),
    ],
)
def test_get_display_image(source_image: str, output: str):
    assert get_display_image(source_image) == output


def test_generate_selected_images():
    product = """
    {
        "code": "5410041040807",
        "product": {
            "images": {
                "1": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1334154510,
                    "uploader": "marianne"
                },
                "13": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 1000,
                            "w": 563
                        }
                    },
                    "uploaded_t": 1486496899,
                    "uploader": "openfood-ch-import"
                },
                "14": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 1000,
                            "w": 563
                        }
                    },
                    "uploaded_t": 1486496900,
                    "uploader": "openfood-ch-import"
                },
                "15": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 1000,
                            "w": 563
                        }
                    },
                    "uploaded_t": 1486496901,
                    "uploader": "openfood-ch-import"
                },
                "16": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 1000,
                            "w": 563
                        }
                    },
                    "uploaded_t": 1486496901,
                    "uploader": "openfood-ch-import"
                },
                "18": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": "1492100649",
                    "uploader": "k13b3r"
                },
                "19": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 75
                        },
                        "400": {
                            "h": 400,
                            "w": 300
                        },
                        "full": {
                            "h": 2666,
                            "w": 2000
                        }
                    },
                    "uploaded_t": "1492100888",
                    "uploader": "k13b3r"
                },
                "2": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1334154562,
                    "uploader": "marianne"
                },
                "20": {
                    "sizes": {
                        "100": {
                            "h": 37,
                            "w": 100
                        },
                        "400": {
                            "h": 146,
                            "w": 400
                        },
                        "full": {
                            "h": 750,
                            "w": 2050
                        }
                    },
                    "uploaded_t": "1516747268",
                    "uploader": "kiliweb"
                },
                "21": {
                    "sizes": {
                        "100": {
                            "h": 60,
                            "w": 100
                        },
                        "400": {
                            "h": 241,
                            "w": 400
                        },
                        "full": {
                            "h": 1203,
                            "w": 2000
                        }
                    },
                    "uploaded_t": "1519822077",
                    "uploader": "openfoodfacts-contributors"
                },
                "22": {
                    "sizes": {
                        "100": {
                            "h": 34,
                            "w": 100
                        },
                        "400": {
                            "h": 137,
                            "w": 400
                        },
                        "full": {
                            "h": 1130,
                            "w": 3311
                        }
                    },
                    "uploaded_t": 1535996246,
                    "uploader": "asmoth"
                },
                "23": {
                    "sizes": {
                        "100": {
                            "h": 26,
                            "w": 100
                        },
                        "400": {
                            "h": 103,
                            "w": 400
                        },
                        "full": {
                            "h": 996,
                            "w": 3870
                        }
                    },
                    "uploaded_t": 1535996264,
                    "uploader": "asmoth"
                },
                "24": {
                    "sizes": {
                        "100": {
                            "h": 34,
                            "w": 100
                        },
                        "400": {
                            "h": 136,
                            "w": 400
                        },
                        "full": {
                            "h": 1015,
                            "w": 2996
                        }
                    },
                    "uploaded_t": 1535996280,
                    "uploader": "asmoth"
                },
                "25": {
                    "sizes": {
                        "100": {
                            "h": 29,
                            "w": 100
                        },
                        "400": {
                            "h": 118,
                            "w": 400
                        },
                        "full": {
                            "h": 1074,
                            "w": 3653
                        }
                    },
                    "uploaded_t": 1535996307,
                    "uploader": "asmoth"
                },
                "26": {
                    "sizes": {
                        "100": {
                            "h": 96,
                            "w": 100
                        },
                        "400": {
                            "h": 383,
                            "w": 400
                        },
                        "full": {
                            "h": 1822,
                            "w": 1904
                        }
                    },
                    "uploaded_t": 1535996328,
                    "uploader": "asmoth"
                },
                "27": {
                    "sizes": {
                        "100": {
                            "h": 98,
                            "w": 100
                        },
                        "400": {
                            "h": 393,
                            "w": 400
                        },
                        "full": {
                            "h": 1980,
                            "w": 2017
                        }
                    },
                    "uploaded_t": 1535996342,
                    "uploader": "asmoth"
                },
                "3": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1334154785,
                    "uploader": "marianne"
                },
                "31": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 2611,
                            "w": 1469
                        }
                    },
                    "uploaded_t": 1542482438,
                    "uploader": "openfoodfacts-contributors"
                },
                "32": {
                    "sizes": {
                        "100": {
                            "h": 48,
                            "w": 100
                        },
                        "400": {
                            "h": 192,
                            "w": 400
                        },
                        "full": {
                            "h": 1665,
                            "w": 3472
                        }
                    },
                    "uploaded_t": 1550682014,
                    "uploader": "axelbrct"
                },
                "33": {
                    "sizes": {
                        "100": {
                            "h": 56,
                            "w": 100
                        },
                        "400": {
                            "h": 225,
                            "w": 400
                        },
                        "full": {
                            "h": 563,
                            "w": 1000
                        }
                    },
                    "uploaded_t": 1554307269,
                    "uploader": "foodrepo"
                },
                "34": {
                    "sizes": {
                        "100": {
                            "h": 56,
                            "w": 100
                        },
                        "400": {
                            "h": 225,
                            "w": 400
                        },
                        "full": {
                            "h": 563,
                            "w": 1000
                        }
                    },
                    "uploaded_t": 1554307269,
                    "uploader": "foodrepo"
                },
                "35": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 56
                        },
                        "400": {
                            "h": 400,
                            "w": 225
                        },
                        "full": {
                            "h": 1000,
                            "w": 563
                        }
                    },
                    "uploaded_t": 1554307269,
                    "uploader": "foodrepo"
                },
                "36": {
                    "sizes": {
                        "100": {
                            "h": 56,
                            "w": 100
                        },
                        "400": {
                            "h": 225,
                            "w": 400
                        },
                        "full": {
                            "h": 563,
                            "w": 1000
                        }
                    },
                    "uploaded_t": 1554307270,
                    "uploader": "foodrepo"
                },
                "37": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 100
                        },
                        "400": {
                            "h": 399,
                            "w": 400
                        },
                        "full": {
                            "h": 1543,
                            "w": 1548
                        }
                    },
                    "uploaded_t": 1570434650,
                    "uploader": "openfoodfacts-contributors"
                },
                "38": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 75
                        },
                        "400": {
                            "h": 400,
                            "w": 300
                        },
                        "full": {
                            "h": 3264,
                            "w": 2448
                        }
                    },
                    "uploaded_t": "1462880728",
                    "uploader": "openfoodfacts-contributors"
                },
                "39": {
                    "sizes": {
                        "100": {
                            "h": 29,
                            "w": 100
                        },
                        "400": {
                            "h": 117,
                            "w": 400
                        },
                        "full": {
                            "h": 1070,
                            "w": 3659
                        }
                    },
                    "uploaded_t": 1580714081,
                    "uploader": "hungergames"
                },
                "4": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1334155058,
                    "uploader": "marianne"
                },
                "40": {
                    "sizes": {
                        "100": {
                            "h": 26,
                            "w": 100
                        },
                        "400": {
                            "h": 105,
                            "w": 400
                        },
                        "full": {
                            "h": 1061,
                            "w": 4048
                        }
                    },
                    "uploaded_t": 1580714100,
                    "uploader": "hungergames"
                },
                "41": {
                    "sizes": {
                        "100": {
                            "h": 32,
                            "w": 100
                        },
                        "400": {
                            "h": 127,
                            "w": 400
                        },
                        "full": {
                            "h": 1169,
                            "w": 3694
                        }
                    },
                    "uploaded_t": 1580714149,
                    "uploader": "hungergames"
                },
                "42": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 3036,
                            "w": 4048
                        }
                    },
                    "uploaded_t": 1580714186,
                    "uploader": "hungergames"
                },
                "43": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 75
                        },
                        "400": {
                            "h": 400,
                            "w": 300
                        },
                        "full": {
                            "h": 4048,
                            "w": 3036
                        }
                    },
                    "uploaded_t": 1580714198,
                    "uploader": "hungergames"
                },
                "44": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 50
                        },
                        "400": {
                            "h": 400,
                            "w": 200
                        },
                        "full": {
                            "h": 2612,
                            "w": 1306
                        }
                    },
                    "uploaded_t": 1605026776,
                    "uploader": "openfoodfacts-contributors"
                },
                "45": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 75
                        },
                        "400": {
                            "h": 400,
                            "w": 300
                        },
                        "full": {
                            "h": 4032,
                            "w": 3024
                        }
                    },
                    "uploaded_t": 1623677280,
                    "uploader": "oliviers"
                },
                "46": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 100
                        },
                        "400": {
                            "h": 399,
                            "w": 400
                        },
                        "full": {
                            "h": 509,
                            "w": 510
                        }
                    },
                    "uploaded_t": 1631113563,
                    "uploader": "thaialagata"
                },
                "47": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 100
                        },
                        "400": {
                            "h": 400,
                            "w": 400
                        },
                        "full": {
                            "h": 1200,
                            "w": 1200
                        }
                    },
                    "uploaded_t": 1632673131,
                    "uploader": "thaialagata"
                },
                "48": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 2448,
                            "w": 3264
                        }
                    },
                    "uploaded_t": 1660634782,
                    "uploader": "oc84"
                },
                "49": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 2448,
                            "w": 3264
                        }
                    },
                    "uploaded_t": 1660634830,
                    "uploader": "oc84"
                },
                "5": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1334155092,
                    "uploader": "marianne"
                },
                "50": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 2448,
                            "w": 3264
                        }
                    },
                    "uploaded_t": 1660634898,
                    "uploader": "oc84"
                },
                "51": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 2448,
                            "w": 3264
                        }
                    },
                    "uploaded_t": 1660634969,
                    "uploader": "oc84"
                },
                "52": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 2448,
                            "w": 3264
                        }
                    },
                    "uploaded_t": 1660635055,
                    "uploader": "oc84"
                },
                "6": {
                    "sizes": {
                        "100": {
                            "h": 60,
                            "w": 100
                        },
                        "400": {
                            "h": 240,
                            "w": 400
                        },
                        "full": {
                            "h": 480,
                            "w": 800
                        }
                    },
                    "uploaded_t": 1361885080,
                    "uploader": "openfoodfacts-contributors"
                },
                "7": {
                    "sizes": {
                        "100": {
                            "h": 100,
                            "w": 75
                        },
                        "400": {
                            "h": 400,
                            "w": 299
                        },
                        "full": {
                            "h": 2592,
                            "w": 1936
                        }
                    },
                    "uploaded_t": 1371724550,
                    "uploader": "openfoodfacts-contributors"
                },
                "8": {
                    "sizes": {
                        "100": {
                            "h": 45,
                            "w": 100
                        },
                        "400": {
                            "h": 179,
                            "w": 400
                        },
                        "full": {
                            "h": 894,
                            "w": 2000
                        }
                    },
                    "uploaded_t": 1419344271,
                    "uploader": "miles67off"
                },
                "9": {
                    "sizes": {
                        "100": {
                            "h": 75,
                            "w": 100
                        },
                        "400": {
                            "h": 300,
                            "w": 400
                        },
                        "full": {
                            "h": 1500,
                            "w": 2000
                        }
                    },
                    "uploaded_t": "1452534788",
                    "uploader": "k13b3r"
                },
                "front": {
                    "geometry": "1585x485-105-440",
                    "imgid": "2",
                    "normalize": null,
                    "rev": "4",
                    "sizes": {
                        "100": {
                            "h": 31,
                            "w": 100
                        },
                        "200": {
                            "h": 61,
                            "w": 200
                        },
                        "400": {
                            "h": 122,
                            "w": 400
                        },
                        "full": {
                            "h": 485,
                            "w": 1585
                        }
                    },
                    "white_magic": "checked"
                },
                "front_es": {
                    "angle": "0",
                    "coordinates_image_size": "full",
                    "geometry": "0x0-0-0",
                    "imgid": "47",
                    "normalize": "false",
                    "rev": "130",
                    "sizes": {
                        "100": {
                            "h": 34,
                            "w": 100
                        },
                        "200": {
                            "h": 67,
                            "w": 200
                        },
                        "400": {
                            "h": 134,
                            "w": 400
                        },
                        "full": {
                            "h": 402,
                            "w": 1200
                        }
                    },
                    "white_magic": "false",
                    "x1": "0",
                    "x2": "0",
                    "y1": "0",
                    "y2": "0"
                },
                "front_fr": {
                    "angle": "0",
                    "coordinates_image_size": "full",
                    "geometry": "3064x998-158-720",
                    "imgid": "48",
                    "normalize": "false",
                    "rev": "142",
                    "sizes": {
                        "100": {
                            "h": 33,
                            "w": 100
                        },
                        "200": {
                            "h": 65,
                            "w": 200
                        },
                        "400": {
                            "h": 130,
                            "w": 400
                        },
                        "full": {
                            "h": 998,
                            "w": 3064
                        }
                    },
                    "white_magic": "false",
                    "x1": "158.6092266613924",
                    "x2": "3222.9130241297466",
                    "y1": "720.5130661590189",
                    "y2": "1718.9940788172466"
                },
                "ingredients": {
                    "geometry": "1490x200-180-480",
                    "imgid": "5",
                    "normalize": null,
                    "rev": "11",
                    "sizes": {
                        "100": {
                            "h": 13,
                            "w": 100
                        },
                        "200": {
                            "h": 27,
                            "w": 200
                        },
                        "400": {
                            "h": 54,
                            "w": 400
                        },
                        "full": {
                            "h": 200,
                            "w": 1490
                        }
                    },
                    "white_magic": null
                },
                "ingredients_fr": {
                    "angle": "0",
                    "coordinates_image_size": "full",
                    "geometry": "971x476-530-974",
                    "imgid": "51",
                    "normalize": "false",
                    "rev": "144",
                    "sizes": {
                        "100": {
                            "h": 49,
                            "w": 100
                        },
                        "200": {
                            "h": 98,
                            "w": 200
                        },
                        "400": {
                            "h": 196,
                            "w": 400
                        },
                        "full": {
                            "h": 476,
                            "w": 971
                        }
                    },
                    "white_magic": "false",
                    "x1": "530.4573279272151",
                    "x2": "1501.3940367879745",
                    "y1": "974.9542869857594",
                    "y2": "1450.0935274920885"
                },
                "nutrition": {
                    "geometry": "0x0--5--4",
                    "imgid": "8",
                    "normalize": "checked",
                    "rev": "23",
                    "sizes": {
                        "100": {
                            "h": 45,
                            "w": 100
                        },
                        "200": {
                            "h": 89,
                            "w": 200
                        },
                        "400": {
                            "h": 179,
                            "w": 400
                        },
                        "full": {
                            "h": 894,
                            "w": 2000
                        }
                    },
                    "white_magic": null
                },
                "nutrition_fr": {
                    "angle": "0",
                    "coordinates_image_size": "full",
                    "geometry": "881x427-1501-937",
                    "imgid": "51",
                    "normalize": "false",
                    "rev": "145",
                    "sizes": {
                        "100": {
                            "h": 48,
                            "w": 100
                        },
                        "200": {
                            "h": 97,
                            "w": 200
                        },
                        "400": {
                            "h": 194,
                            "w": 400
                        },
                        "full": {
                            "h": 427,
                            "w": 881
                        }
                    },
                    "white_magic": "false",
                    "x1": "1501.3940367879745",
                    "x2": "2382.8117583069616",
                    "y1": "937.4230926127373",
                    "y2": "1364.3598014734966"
                },
                "packaging_fr": {
                    "angle": "0",
                    "coordinates_image_size": "full",
                    "geometry": "661x165-220-1100",
                    "imgid": "49",
                    "normalize": "false",
                    "rev": "146",
                    "sizes": {
                        "100": {
                            "h": 25,
                            "w": 100
                        },
                        "200": {
                            "h": 50,
                            "w": 200
                        },
                        "400": {
                            "h": 100,
                            "w": 400
                        },
                        "full": {
                            "h": 165,
                            "w": 661
                        }
                    },
                    "white_magic": "false",
                    "x1": "220.58391020569618",
                    "x2": "881.6472013449367",
                    "y1": "1100.5069657337815",
                    "y2": "1265.7727885185916"
                }
            }
        },
        "status": 1,
        "status_verbose": "product found"
    }
    """

    images = dict(loads(product))

    selected_images = CategoryQuestionFormatter.generate_selected_images(
        images["product"]["images"], images["code"]
    )
    assert selected_images["selected_images"]["front"] == {
        "display": {
            "es": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_es.130.400.jpg",
            "fr": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_fr.142.400.jpg",
        }
    }
    assert selected_images["selected_images"]["small"] == {
        "es": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_es.130.200.jpg",
        "fr": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_fr.142.200.jpg",
    }
    assert selected_images["selected_images"]["thumb"] == {
        "es": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_es.130.100.jpg",
        "fr": "https://images.openfoodfacts.org/images/products/541/004/104/0807/front_fr.142.100.jpg",
    }
