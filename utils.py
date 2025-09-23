from copy import deepcopy
import json

class MergeTypeError(TypeError):
    pass

def deep_merge(a, b, *,
               list_strategy='extend',   # 'extend' | 'unique' | 'by_index' | 'by_key'
               list_key=None,            # ключ для 'by_key'
               conflict='right',         # 'right' | 'left' | 'raise' | 'both'
               _level=0):
    """
    Глубокий merge двух структур из dict/list/скаляров.

    Правила:
      - dict+dict: слияние по ключам, значения рекурсивно.
      - list+list: по стратегии list_strategy.
      - типы не совпали: conflict определяет поведение:
          'right' -> вернуть b
          'left'  -> вернуть a
          'raise' -> кинуть MergeTypeError
          'both'  -> вернуть [a, b]
    """
    # Быстрые тривиальные случаи
    if a is b:
        return a
    if a is None:
        return deepcopy(b)
    if b is None:
        return deepcopy(a)

    # dict + dict
    if isinstance(a, dict) and isinstance(b, dict):
        out = {}
        # сначала копия a
        for k, v in a.items():
            out[k] = deepcopy(v)
        # затем мержим b
        for k, v in b.items():
            if k in out:
                out[k] = deep_merge(out[k], v,
                                   list_strategy=list_strategy,
                                   list_key=list_key,
                                   conflict=conflict,
                                   _level=_level+1)
            else:
                out[k] = deepcopy(v)
        return out

    # list + list
    if isinstance(a, list) and isinstance(b, list):
        if list_strategy == 'extend':
            return deepcopy(a) + deepcopy(b)

        if list_strategy == 'unique':
            seen = set()
            out = []
            for item in a + b:
                marker = _hashable_marker(item)
                if marker not in seen:
                    seen.add(marker)
                    out.append(deepcopy(item))
            return out

        if list_strategy == 'by_index':
            out = []
            la, lb = len(a), len(b)
            m = min(la, lb)
            for i in range(m):
                out.append(
                    deep_merge(a[i], b[i],
                               list_strategy=list_strategy,
                               list_key=list_key,
                               conflict=conflict,
                               _level=_level+1)
                )
            # остаток более длинного списка
            tail = a[m:] if la > lb else b[m:]
            out.extend(deepcopy(tail))
            return out

        if list_strategy == 'by_key':
            if not list_key:
                raise ValueError("list_key обязателен для стратегии 'by_key'.")

            # Индексация по ключу
            index = {}
            order = []  # сохраняем общий порядок появления ключей
            def add_item(it, source):
                if isinstance(it, dict) and list_key in it:
                    k = it[list_key]
                    if k not in index:
                        index[k] = deepcopy(it)
                        order.append((k, source))
                    else:
                        index[k] = deep_merge(index[k], it,
                                              list_strategy=list_strategy,
                                              list_key=list_key,
                                              conflict=conflict,
                                              _level=_level+1)
                else:
                    # Элемент без ключа просто добавим с уникальным маркером
                    order.append((object(), source))
                    index[order[-1][0]] = deepcopy(it)

            for it in a:
                add_item(it, 'a')
            for it in b:
                add_item(it, 'b')

            # восстанавливаем порядок: сначала те, что встречались в a, потом новые из b
            # но мы уже добавляли в порядке добавления, так что просто собрать
            out = []
            for k, _src in order:
                # может быть дубликат пары (k, 'a') и потом (k, 'b'); мы оставляем одно,
                # потому что index[k] уже содержит слитое значение
                if k is not None:
                    # защищаемся от повторов в order
                    if not out or out[-1] is not index[k]:
                        out.append(index[k])
            # Удалим возможные повторяющиеся ссылки
            unique_out = []
            added_ids = set()
            for item in out:
                if id(item) not in added_ids:
                    unique_out.append(item)
                    added_ids.add(id(item))
            return unique_out

        raise ValueError(f"Неизвестная стратегия списка: {list_strategy}")

    # типы не совпали или скаляр+что-то
    if conflict == 'right':
        return deepcopy(b)
    if conflict == 'left':
        return deepcopy(a)
    if conflict == 'both':
        return [deepcopy(a), deepcopy(b)]
    if conflict == 'raise':
        raise MergeTypeError(f"Конфликт типов на уровне {_level}: {type(a).__name__} vs {type(b).__name__}")
    raise ValueError(f"Неизвестная политика conflict: {conflict}")


def _hashable_marker(x):
    """Делаем маркер для сравнения уникальности в списках."""
    if isinstance(x, dict):
        return ('dict', tuple(sorted((k, _hashable_marker(v)) for k, v in x.items())))
    if isinstance(x, list):
        return ('list', tuple(_hashable_marker(i) for i in x))
    try:
        hash(x)
        return ('scalar', x)
    except TypeError:
        return ('repr', repr(x))


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
