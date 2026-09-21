import unittest
from collections import Counter

from ser.data.splits import speaker_folds


class SpeakerSplitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = []
        for corpus in ("ravdess", "crema-d"):
            for speaker in range(10):
                for sample in range(2 + speaker % 3):
                    self.metadata.append(
                        {
                            "corpus": corpus,
                            "speaker": str(speaker),
                            "gender": "female" if speaker % 2 else "male",
                            "sample": sample,
                        }
                    )

    @staticmethod
    def speakers(records, indices):
        return {f"{records[index]['corpus']}:{records[index]['speaker']}" for index in indices}

    def test_no_leakage_and_complete_test_coverage(self) -> None:
        folds = speaker_folds(self.metadata, n_folds=5, seed=11)
        test_counts = Counter()
        for split in folds:
            train = self.speakers(self.metadata, split["train"])
            validation = self.speakers(self.metadata, split["val"])
            test = self.speakers(self.metadata, split["test"])
            self.assertTrue(train.isdisjoint(validation))
            self.assertTrue(train.isdisjoint(test))
            self.assertTrue(validation.isdisjoint(test))
            self.assertEqual(sum(map(len, split.values())), len(self.metadata))
            test_counts.update(test)
        expected = {f"{row['corpus']}:{row['speaker']}" for row in self.metadata}
        self.assertEqual(set(test_counts), expected)
        self.assertTrue(all(count == 1 for count in test_counts.values()))

    def test_namespaces_same_raw_speaker(self) -> None:
        folds = speaker_folds(self.metadata, n_folds=5, seed=11)
        all_test = [self.speakers(self.metadata, split["test"]) for split in folds]
        ravdess_fold = next(i for i, group in enumerate(all_test) if "ravdess:1" in group)
        crema_fold = next(i for i, group in enumerate(all_test) if "crema-d:1" in group)
        self.assertIsInstance(ravdess_fold, int)
        self.assertIsInstance(crema_fold, int)

    def test_deterministic(self) -> None:
        self.assertEqual(
            speaker_folds(self.metadata, n_folds=5, seed=99),
            speaker_folds(self.metadata, n_folds=5, seed=99),
        )


if __name__ == "__main__":
    unittest.main()
